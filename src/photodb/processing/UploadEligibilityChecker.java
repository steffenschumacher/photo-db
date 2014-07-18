/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package photodb.processing;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.xml.ws.BindingProvider;
import photodb.concurrent.BufferedExecutor;
import photodb.config.Config;
import photodb.config.NotInitializedException;
import photodb.wsclient.PhotoDBWS;
import photodb.wsclient.PhotoDBWS_Service;
import photodb.wsclient.SoapPhoto;

/**
 * Thread for dispatching uploadEligibility checks in bulks of 20 for efficiency
 *
 * @author ssch
 */
public class UploadEligibilityChecker extends BufferedExecutor<SoapPhoto, Boolean> {

    private final static Logger LOG = Logger.getLogger(UploadEligibilityChecker.class.getName());

    //<editor-fold defaultstate="collapsed" desc="Singleton">
    private static class UploadEligibilityCheckerHolder {

        public static final UploadEligibilityChecker instance = new UploadEligibilityChecker();

        static {
            instance.start();
        }
    }

    public static UploadEligibilityChecker getInstance() {
        return UploadEligibilityCheckerHolder.instance;
    }
    //</editor-fold>

    private final PhotoDBWS port;

    private UploadEligibilityChecker() {
        super("UploadEligibilityCheckerThread", 20, 1000);
        PhotoDBWS_Service service = new PhotoDBWS_Service();
        port = service.getPhotoDBWSPort();
        BindingProvider bp = (BindingProvider) port;
        try {
            String wsdlUrl = Config.getInstance().getWsUrl();
            if (wsdlUrl == null) {
                wsdlUrl = "http://localhost:8084/PhotoDbWS/PhotoDBWS";
            }
            bp.getRequestContext().put(
                    BindingProvider.ENDPOINT_ADDRESS_PROPERTY,
                    wsdlUrl);
        } catch (NotInitializedException ex) {
            LOG.log(Level.SEVERE, "Bug?", ex);
            System.exit(0);
        }

    }

    /**
     * Checks if a given photo is eligible for upload, using the bulk ws method.
     * The photo is added to a job queue, which in return yields a Future
     * object. The get() of this Future object will yield the eligibility of the
     * submitted photo.
     *
     * @param sp photo to be checked
     * @return boolean indicating that the photo was eligible for upload
     */
    public boolean check(SoapPhoto sp) {
        final int timeoutSeconds = 30;
        Future<Boolean> result;
        try {
            result = this.submit(sp, timeoutSeconds, TimeUnit.SECONDS);
        } catch (InterruptedException ex) {
            LOG.log(Level.SEVERE, "Interrupted while submitting check for " + sp.toString(), ex);
            return false;
        } catch (TimeoutException ex) {
            LOG.log(Level.SEVERE, "Failed to submit {1} within {0} seconds",
                    new Object[]{timeoutSeconds, sp.toString()});
            return false;
        }
        try {
            return result.get(timeoutSeconds, TimeUnit.SECONDS);
        } catch (InterruptedException ex) {
            LOG.log(Level.SEVERE, "Interrupted while waiting for result of " + sp.toString(), ex);
        } catch (TimeoutException ex) {
            LOG.log(Level.SEVERE, "Failed to get result for {1} within {0} seconds",
                    new Object[]{timeoutSeconds, sp.toString()});
        } catch (ExecutionException ex) {
            LOG.log(Level.SEVERE, "Unexpected exception for " + sp.toString(), ex);
        }
        return false;
    }

    /**
     * Executes the actual call to the web service in a bulk fashion.
     * Each job is subsequently completed as required
     */
    @Override
    protected void executeJobs() {
        List<SoapPhoto> arg = new ArrayList<>(getInputs());
        List<SoapPhoto> reply = port.isArrayUploadEligible(arg);
        for (SoapPhoto sp : reply) {
            completeJob(sp, sp.isEligible());
        }
    }
}
