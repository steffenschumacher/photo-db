package photodb.processing;

import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * ScanFolderTask - short description.
 * Detailed description.
 * 
 * @author  Steffen Schumacher
 * @version 1.0
 */
class ScanFolderTask implements Runnable {
    private static final Semaphore _activeSubFolderScans = new Semaphore(0);
    private static final Semaphore _scansDoneSemaphore = new Semaphore(0);
    private final static Logger LOG = Logger.getLogger(ScanFolderTask.class.getName());
    private final String path;
    private final FolderScanner parent;

    public ScanFolderTask(String path, FolderScanner parent) {
        _activeSubFolderScans.release();
        this.path = path;
        this.parent = parent;
    }

    @Override
    public void run() {
        FolderScanner fs = new FolderScanner(path, parent);
        fs.queuePhotoJobs();
        try {
            _activeSubFolderScans.acquire();
            if(_activeSubFolderScans.availablePermits() == 0) {
                LOG.log(Level.FINE, "Releasing ScansDoneSemaphore after Scanning {0}", path);
                _scansDoneSemaphore.release();
            }
        } catch (InterruptedException ex) {
            LOG.log(Level.SEVERE, "Interrupted while acquiring semaphore", ex);
        }
    }
    
    public static boolean waitForAllFoldersScanned(long t, TimeUnit tu) {
        try {
            boolean success = _scansDoneSemaphore.tryAcquire(t, tu);
            if(success) {
                _scansDoneSemaphore.release();  //Release it again, so we maintain state
            }
            return success;
        } catch (InterruptedException ex) {
            LOG.log(Level.SEVERE, "Interrupted while waiting for all subfolders to be scanned", ex);
            return false;
        }
    }
    
}
