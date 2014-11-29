package photodb;

import java.io.IOException;
import java.util.concurrent.TimeUnit;
import java.util.logging.ConsoleHandler;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.Logger;
import photodb.clArgs.Parser;
import photodb.config.Config;
import photodb.config.NotInitializedException;
import photodb.log.ConsoleFormatter;
import photodb.processing.FolderScanner;
import photodb.processing.ScanPhotoTask;

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
        Logger.getLogger("photodb").setUseParentHandlers(false);
        Logger.getLogger("photodb").setLevel(lvl);
        Logger.getLogger("photodb").addHandler(h);
    }
    
    /**
     * @param args the command line arguments
     * @throws java.lang.InterruptedException
     */
    public static void main(String[] args) throws InterruptedException {    
        final Logger LOG = Logger.getLogger("photodb");
        
        final String searchPath;
        try {
            searchPath = Parser.parseArguments(args);
            for(Handler h : LOG.getHandlers()) {
                h.setLevel(Config.getInstance().getLogLevel());
            }
            LOG.setLevel(Config.getInstance().getLogLevel());
            if(Config.getInstance().getWsUrl() != null) {
                ScanPhotoTask.initForRemoteDb();
            } else {
                ScanPhotoTask.initForLocalDb(Config.getInstance().getLibPath());
            }
            
            
        } catch (IOException ex) {
            LOG.log(Level.SEVERE, "Exception parsing arguments?", ex);
            return;
        } catch (NotInitializedException ex) {
            LOG.log(Level.SEVERE, "Config not initialized??", ex);
            return;
        } catch (Exception ex) {
            LOG.log(Level.SEVERE, null, ex);
            return;
        }
        LOG.log(Level.FINE, "test");
        
        //ScanPhotoTask.initForRemoteDb(null);
        FolderScanner fs = new FolderScanner(searchPath);
        while(!fs.awaitQueueTermination(10, TimeUnit.SECONDS)) {
            LOG.log(Level.FINE, 
                    "Waiting for all photos to be processed (found/processed): {0}/{1}", 
                    new Object[]{FolderScanner.getPhotoCount(), FolderScanner.getProcessedCount()});
        }
        LOG.log(Level.FINE, 
                    "Done with all photos to be processed (found/processed): {0}/{1}", 
                    new Object[]{FolderScanner.getPhotoCount(), FolderScanner.getProcessedCount()});
        ScanPhotoTask.cleanup();
    }
    
    
}
