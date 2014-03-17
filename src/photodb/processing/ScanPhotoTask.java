package photodb.processing;

import com.drew.imaging.ImageProcessingException;
import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;
import photodb.photo.FilePhoto;

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
            FilePhoto fp = new FilePhoto(path);
            LOG.log(Level.FINE, "Scanned {0}", fp.toString());
        } catch (ImageProcessingException | IOException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception for " + path, ex);
        }
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
