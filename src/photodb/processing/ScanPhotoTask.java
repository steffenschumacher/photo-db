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
    private final static Logger LOG = Logger.getLogger(FolderScanner.class.getName());
    private static Integer processed = 0;
    private final String path;

    public ScanPhotoTask(String path) {
        this.path = path;
    }

    @Override
    public void run() {
        LOG.log(Level.INFO, "Would have scanned image at: {0}", path);
        synchronized(LOG) {
            processed++;
        }
    }
    
    public static int getProcessed() {
        synchronized(LOG) {
            return processed;
        }
    }
    
    
    
    
}
