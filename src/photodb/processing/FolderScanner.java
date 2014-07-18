package photodb.processing;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Pattern;

/**
 * FolderScanner - short description. Detailed description.
 *
 * @author Steffen Schumacher
 * @version 1.0
 */
public class FolderScanner {

    //<editor-fold defaultstate="collapsed" desc="local singleton ExecutorService to deal with threading.">
    private static ExecutorService _QUEUE;

    private static ExecutorService getQueue() {
        if (_QUEUE == null) {
            initQueue();
        }
        return _QUEUE;
    }

    private synchronized static void initQueue() {
        if (_QUEUE == null) {
            _QUEUE = Executors.newFixedThreadPool(5);
        }
    }

    //</editor-fold>
    private final static Pattern _patImage = Pattern.compile(".*\\.(jp(eg|g)|arw)", Pattern.CASE_INSENSITIVE);
    private final static Logger LOG = Logger.getLogger(FolderScanner.class.getName());
    private static Integer photos = 0;

    private final String path;
    private final ArrayList<String> photosToBeProcessed;
    private final FolderScanner parent;

    protected FolderScanner(String path, FolderScanner parent) {
        this.path = path;
        this.parent = parent;
        photosToBeProcessed = new ArrayList<>();
        scanPath();
        addPhotoCount(photosToBeProcessed.size());
    }

    public FolderScanner(String path) {
        this(path, null);
        queuePhotoJobs();
        while (!ScanFolderTask.waitForAllFoldersScanned(10, TimeUnit.SECONDS)) {
            LOG.log(Level.FINE,
                    "Waiting for all subfolder/photos to be queued, Photos (found/processed): {0}/{1}",
                    new Object[]{getPhotoCount(), getProcessedCount()});
        }
        LOG.log(Level.FINE,
                    "All subfolder/photos have been queued, (found/processed): {0}/{1}",
                    new Object[]{getPhotoCount(), getProcessedCount()});
        getQueue().shutdown();  //All tasks have been queued now..
    }

    private void scanPath() {
        File folder = new File(path);
        File[] listOfFiles = folder.listFiles();
        if (parent == null) {
            ScanFolderTask.preventClosing();
        }
        for (File candidate : listOfFiles) {
            final String name = candidate.getName();
            if (candidate.isFile()) {
                if (_patImage.matcher(name).find()) {
                    LOG.log(Level.FINEST, "Queuing a task for image: {0}", name);
                    try {
                        photosToBeProcessed.add(candidate.getCanonicalPath());
                    } catch (IOException ex) {
                        LOG.log(Level.SEVERE, "Unable to retrieve absolute path for " + name, ex);
                    }
                }
            } else if (candidate.isDirectory() && !name.startsWith(".")) {
                try {
                    LOG.log(Level.FINEST, "Queuing a task for folder: {0}", name);
                    ScanFolderTask sft = new ScanFolderTask(candidate.getCanonicalPath(), this);
                    getQueue().execute(sft);
                } catch (IOException ex) {
                    LOG.log(Level.SEVERE, "Unable to retrieve absolute path for " + name, ex);
                }
            }
        }
        if (parent == null) {
            ScanFolderTask.allowClosing();
        }
    }

    public final boolean awaitQueueTermination(long timeout, TimeUnit tu) throws InterruptedException {
        return getQueue().awaitTermination(timeout, tu);
    }

    public final void queuePhotoJobs() {
        for(String photo : photosToBeProcessed) {
            ScanPhotoTask spt = new ScanPhotoTask(photo);
            getQueue().execute(spt);
        }
    }

    private static void addPhotoCount(int value) {
        synchronized (LOG) {
            photos += value;
        }
    }

    public static int getPhotoCount() {
        synchronized (LOG) {
            return photos;
        }
    }

    public static int getProcessedCount() {
        return ScanPhotoTask.getProcessed();
    }
}
