package photodb.processing;

import com.drew.imaging.ImageProcessingException;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.sql.SQLException;
import java.util.logging.Level;
import java.util.logging.Logger;
import photodb.db.Database;
import photodb.db.ExistingPhotoException;
import photodb.photo.FilePhoto;
import photodb.photo.PhotoTooSmallException;

/**
 * ScanPhotoTask - short description. Detailed description.
 *
 * @author Steffen Schumacher
 * @version 1.0
 */
public class ScanPhotoTask extends PhotoController implements Runnable {

    private final static Logger LOG = Logger.getLogger(ScanPhotoTask.class.getName());
    private static final String s_store = "/Users/ssch/PhotoDb";
    private static Database s_db;

    static {
        try {
            s_db = new Database(s_store + "/photo.db");
        } catch (SQLException ex) {
            LOG.log(Level.SEVERE, null, ex);
        }
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
            if (fp.getShotDate() != null) {
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

    public static int getProcessed() {
        synchronized (LOG) {
            return processed;
        }
    }

}
