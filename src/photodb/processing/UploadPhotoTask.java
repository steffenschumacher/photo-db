/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package photodb.processing;

import java.util.concurrent.RunnableFuture;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.xml.ws.BindingProvider;
import photodb.config.Config;
import photodb.config.NotInitializedException;
import photodb.wsclient.ExistingPhotoWSException;
import photodb.wsclient.PhotoDBWS;
import photodb.wsclient.PhotoDBWS_Service;
import photodb.wsclient.SoapPhoto;

/**
 *
 * @author ssch
 */
public class UploadPhotoTask implements RunnableFuture<ExistingPhotoWSException> {

    private final static Logger LOG = Logger.getLogger(UploadPhotoTask.class.getName());
    private static PhotoDBWS s_port;

    private final SoapPhoto sp;
    private final byte[] data;
    private ExistingPhotoWSException ex;
    private final Semaphore sem;
    private long durationMs;

    public static void initPort() {
        try {
            PhotoDBWS_Service service = new PhotoDBWS_Service();
            s_port = service.getPhotoDBWSPort();
            BindingProvider bp = (BindingProvider) s_port;
            String wsdlUrl = Config.getInstance().getWsUrl();

            if (wsdlUrl == null) {
                wsdlUrl = "http://localhost:8084/PhotoDbWS/PhotoDBWS";
            }
            bp.getRequestContext().put(
                    BindingProvider.ENDPOINT_ADDRESS_PROPERTY,
                    wsdlUrl);
        } catch (NotInitializedException ex) {
            LOG.log(Level.SEVERE, "Unexpected exception", ex);
        }
    }

    public UploadPhotoTask(SoapPhoto sp, byte[] data) {
        this.sp = sp;
        this.data = data;
        sem = new Semaphore(0);
        ex = null;
    }

    @Override
    public void run() {  
        final long start = System.currentTimeMillis();
        try {
            s_port.add(sp, data);
        } catch (ExistingPhotoWSException e) {
            this.ex = e;
        }
        durationMs = System.currentTimeMillis() - start;
        sem.release();//signal completion..
    }

    @Override
    public boolean cancel(boolean mayInterruptIfRunning) {
        throw new UnsupportedOperationException("Not supported yet."); //To change body of generated methods, choose Tools | Templates.
    }

    @Override
    public boolean isCancelled() {
        return false;
    }

    @Override
    public boolean isDone() {
        return sem.availablePermits() == 1;
    }

    @Override
    public ExistingPhotoWSException get() throws InterruptedException {
        sem.acquire();
        sem.release();
        return ex;
    }

    @Override
    public ExistingPhotoWSException get(long timeout, TimeUnit unit) throws InterruptedException, TimeoutException {
        sem.tryAcquire(timeout, unit);
        sem.release();
        return ex;
    }

    public long getDurationMs() {
        try {
            sem.acquire();
            sem.release();
            return durationMs;
        } catch (InterruptedException ex) {
            LOG.log(Level.SEVERE, null, ex);
        }
        return 0;
    }
    
    

}
