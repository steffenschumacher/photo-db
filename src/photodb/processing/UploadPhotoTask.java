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
import javax.xml.datatype.DatatypeConfigurationException;
import javax.xml.ws.BindingProvider;
import photodb.config.Config;
import photodb.config.NotInitializedException;
import photodb.wsclient.ExistingPhotoWSException;
import photodb.wsclient.PhotoDBWS;
import photodb.wsclient.PhotoDBWS_Service;
import photodb.photo.SoapPhoto;

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

    public static void initPort() throws Exception {
        try {
            PhotoDBWS_Service service = new PhotoDBWS_Service();
            s_port = service.getPhotoDBWSPort();
            BindingProvider bp = (BindingProvider) s_port;
            String wsdlUrl = Config.getInstance().getWsUrl();

            if (wsdlUrl == null) {
                throw new Exception("Missing wsdl URL from config");
            }
            LOG.log(Level.FINE, "Using {0} as wsdl url..", wsdlUrl);
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
            s_port.add(marshalSoapPhoto(sp), data);
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

    private static photodb.wsclient.SoapPhoto marshalSoapPhoto(photodb.photo.SoapPhoto sp) {
        photodb.wsclient.SoapPhoto SoapPhoto = new photodb.wsclient.SoapPhoto();
        SoapPhoto.setCamera(sp.getCamera());
        SoapPhoto.setFileName(sp.getFileName());
        SoapPhoto.setFileNameNoExtention(sp.getFileNameNoExtention());
        SoapPhoto.setHRes(sp.getHRes());
        SoapPhoto.setVRes(sp.getVRes());
        try {
            SoapPhoto.setShotDate(sp.getShotDateXML());
        } catch (DatatypeConfigurationException ex) {
            LOG.log(Level.SEVERE, "Funky exception", ex);
        }
        return SoapPhoto;
    }

    private static photodb.photo.SoapPhoto unmarshalSoapPhoto(photodb.wsclient.SoapPhoto sp) {
        photodb.photo.SoapPhoto SoapPhoto = new photodb.photo.SoapPhoto();
        SoapPhoto.setCamera(sp.getCamera());
        SoapPhoto.setFileName(sp.getFileName());
        SoapPhoto.setFileNameNoExtention(sp.getFileNameNoExtention());
        SoapPhoto.setHRes(sp.getHRes());
        SoapPhoto.setVRes(sp.getVRes());
        SoapPhoto.setShotDate(sp.getShotDate().toGregorianCalendar().getTime());
        return SoapPhoto;
    }

}
