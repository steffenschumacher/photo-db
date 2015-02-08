package photodb.processing;

import com.drew.imaging.ImageProcessingException;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.sql.SQLException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;
import java.util.logging.Logger;
import photodb.db.Database;
import photodb.db.ExistingPhotoException;
import photodb.photo.FilePhoto;
import photodb.photo.PhotoTooSmallException;
import photodb.wsclient.ExistingPhotoWSException;
import photodb.photo.SoapPhoto;

/**
 * ScanPhotoTask - short description. Detailed description.
 *
 * @author Steffen Schumacher
 * @version 1.0
 */
public class ScanPhotoTask extends PhotoController implements Runnable {

    private final static Logger LOG = Logger.getLogger(ScanPhotoTask.class.getName());
    private static String s_store;
    private static Database s_db;
    private static ExecutorService uploadPool;
    private static boolean isLocal;

    public static void initForLocalDb(String store) {
        LOG.log(Level.FINE, "Setting up shop locally");
        if (store == null) {
            s_store = "/Users/ssch/PhotoDb";
        } else {
            s_store = store;
        }
        try {
            s_db = new Database(s_store + "/photo.db");
            isLocal = true;
        } catch (SQLException ex) {
            LOG.log(Level.SEVERE, null, ex);
        }
    }

    public static void initForRemoteDb() throws Exception {
        LOG.log(Level.INFO, "Setting up shop for remote db..");
        s_store = System.getProperty("java.io.tmpdir") + File.pathSeparator
                + "tmp-photodb-" + System.currentTimeMillis() + ".db";
        try {
            s_db = new Database(s_store);
        } catch (SQLException ex) {
            LOG.log(Level.SEVERE, "Unable to init temporary database", ex);
            System.exit(0);
        }
        UploadPhotoTask.initPort(); //Needs to happen prior to creating tasks
        uploadPool = Executors.newFixedThreadPool(10);  //Allow 10 uploads in parallel
        isLocal = false;
    }

    public static void cleanup() {
        if (isLocal) {
            return;
        }
        s_db.close();
        File tmpDb = new File(s_store);
        tmpDb.deleteOnExit();
        UploadEligibilityChecker.getInstance().terminate();
    }

    private static Integer processed = 0;
    private final String path;

    public ScanPhotoTask(String path) {
        super(s_store, s_db);
        this.path = path;
    }

    @Override
    public void run() {

        try {
            FilePhoto fp = new FilePhoto(path);
            LOG.log(Level.FINE, "Scanned {0}", fp.toString());
            if (fp.satisfiesCriteria()) {
                try {
                    insert(fp);
                } catch (ExistingPhotoException e) {
                    handleExistingPhoto(e, fp);
                }
            } else {
                //TODO: Store files in some way for future walkthrough..
                LOG.log(Level.FINE, "Disregarding {0} because of missing date..", fp);
            }
        } catch (PhotoTooSmallException | FileNotFoundException ex) {
            LOG.log(Level.FINE, "Ignoring {0}: {1}", new Object[]{path, ex.getMessage()});

        } catch (ImageProcessingException | IOException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception for " + path, ex);
        }
        synchronized (LOG) {
            processed++;
        }
    }

    /**
     *
     * @param fp
     * @throws ExistingPhotoException
     * @throws IOException
     */
    @Override
    public void insert(FilePhoto fp) throws ExistingPhotoException, IOException {
        if (isLocal) {
            ExistingPhotoException exphex = super.checkExistence(fp);
            if(exphex == null || exphex.isToBeReplaced()) {    
                LOG.log(Level.INFO, "Stored {0}", new Object[]{fp.toString()});
            } else {
                LOG.log(Level.INFO, 
                        "Ignoring {0} as it is a duplicate of a photo already stored: {1}", 
                        new Object[]{fp.toString(), exphex.getBlockingPhoto().toString()});
            }

        } else {

            SoapPhoto sp = fp.toSOAPObject();
            if (!isUploadEligible(fp)) {
                LOG.log(Level.INFO, "Ignoring {0} as it is a duplicate of a photo already processed in this scan", fp.toString());
            } else if (!UploadEligibilityChecker.getInstance().checkSingle(sp)) {
                LOG.log(Level.INFO, "Ignoring {0} as it already existed remotely", fp.toString());
            } else {
                try {
                    LOG.log(Level.FINE, "Preparing to upload {0}", fp.toString());
                    byte[] data = Files.readAllBytes(Paths.get(fp.getAbsolutePath()));
                    UploadPhotoTask upt = new UploadPhotoTask(sp, data);
                    uploadPool.submit(upt);
                    ExistingPhotoWSException ex = upt.get();
                    if (ex == null) {
                        LOG.log(Level.INFO, "Uploaded {0} in {1} ms",
                                new Object[]{fp.toString(), upt.getDurationMs()});
                    } else {
                        LOG.log(Level.SEVERE,
                                "Attempt to insert photo failed("
                                + fp.getAbsolutePath() + ")", ex);
                    }
                } catch (InterruptedException ex1) {
                    LOG.log(Level.SEVERE, null, ex1);
                }
            }
        }
    }

    /**
     * isUploadEligible checks if the photo exists in the temporary database,
     * which contains the photos uploaded thus far. If the photo exists, it is
     * checked if the blocking photo is eligible to be replaced with the
     * provided one.
     *
     * @param fp
     * @return
     */
    private static boolean isUploadEligible(FilePhoto fp) {
        try {
            s_db.insert(fp);    //Insert the photo into the temp db
        } catch (ExistingPhotoException e) {
            if (!e.isToBeReplaced()) {
                return false;
            } else {
                s_db.delete(e.getBlockingPhoto());
                try {
                    s_db.insert(fp);   //Not expected to throw exceptions due to delete..
                } catch (ExistingPhotoException ex) {
                    LOG.log(Level.SEVERE, "Unexpected exception caught", ex);
                }
            }
        }
        return true;
    }

    public static int getProcessed() {
        synchronized (LOG) {
            return processed;
        }
    }

}
