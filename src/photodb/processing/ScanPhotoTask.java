package photodb.processing;

import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * ScanPhotoTask - short description.
 * Detailed description.
 * 
 * @author  Steffen Schumacher
 * @version 1.0
 */
public class ScanPhotoTask implements Runnable {
    private final static Logger LOG = Logger.getLogger(ScanPhotoTask.class.getName());
    private static Integer processed = 0;
    private final String path;

    public ScanPhotoTask(String path) {
        this.path = path;
    }

    @Override
    public void run() {
        
        try {
            Thread.sleep(System.currentTimeMillis() %4000);
        } catch (InterruptedException ex) {
            LOG.log(Level.SEVERE, "Interrupted", ex);
        }
        synchronized(LOG) {
            processed++;
            LOG.log(Level.FINE, "Would have scanned image at: {0}", path);
        }
    }
    
    public static int getProcessed() {
        synchronized(LOG) {
            return processed;
        }
    }
    
    
    
    
}
