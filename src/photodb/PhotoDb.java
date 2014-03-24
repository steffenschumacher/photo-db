package photodb;

import java.util.concurrent.TimeUnit;
import java.util.logging.ConsoleHandler;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.Logger;
import photodb.log.ConsoleFormatter;
import photodb.processing.FolderScanner;

/**
 *
 * @author Steffen Schumacher
 */
public class PhotoDb {

    static {
        final Level lvl = Level.FINER;
        Handler h = new ConsoleHandler();
        h.setLevel(lvl);
        h.setFormatter(new ConsoleFormatter());
        Logger.getLogger("photodb").setLevel(lvl);
        Logger.getLogger("photodb").addHandler(h);
    }
    
    /**
     * @param args the command line arguments
     * @throws java.lang.InterruptedException
     */
    public static void main(String[] args) throws InterruptedException {

        
        final Logger LOG = Logger.getLogger("photodb");
        
        final String searchPath = "/Volumes/HomeDisk/Billeder/"; ///Users/ssch/USBHD_Backup";
        LOG.log(Level.FINE, "test");
        FolderScanner fs = new FolderScanner(searchPath);
        while(!fs.awaitQueueTermination(3, TimeUnit.SECONDS)) {
            LOG.log(Level.FINE, 
                    "Waiting for all photos to be processed (found/processed): {0}/{1}", 
                    new Object[]{FolderScanner.getPhotoCount(), FolderScanner.getProcessedCount()});
        }
        LOG.log(Level.FINE, 
                    "Done with all photos to be processed (found/processed): {0}/{1}", 
                    new Object[]{FolderScanner.getPhotoCount(), FolderScanner.getProcessedCount()});
        
    }
    
    
}
