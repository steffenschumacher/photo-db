package photodb.processing;

import com.drew.imaging.ImageProcessingException;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.channels.FileChannel;
import java.sql.SQLException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.logging.Level;
import java.util.logging.Logger;
import photodb.db.Database;
import photodb.db.ExistingPhotoException;
import photodb.photo.FilePhoto;
import photodb.photo.Photo;
import photodb.photo.PhotoTooSmallException;

/**
 * ScanPhotoTask - short description. Detailed description.
 *
 * @author Steffen Schumacher
 * @version 1.0
 */
public class ScanPhotoTask implements Runnable {

    private final static Logger LOG = Logger.getLogger(ScanPhotoTask.class.getName());
    private static final String store = "/Users/ssch/PhotoDb";
    private static Database db;

    static {
        try {
            db = new Database(store + "/photo.db");
        } catch (SQLException ex) {
            LOG.log(Level.SEVERE, null, ex);
        }
    }

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
        } catch(PhotoTooSmallException | FileNotFoundException ex) {
            LOG.log(Level.FINE, "Ignoring {0}: {1}", new Object[]{path, ex.getMessage()});
                    
        } catch (ImageProcessingException | IOException ex) {
            LOG.log(Level.SEVERE, "Unhandled exception for " + path, ex);
        } 
        synchronized (LOG) {
            processed++;
        }
    }

    protected void insert(FilePhoto fp) throws ExistingPhotoException, IOException {
        db.insert(fp);
        LOG.log(Level.FINE, "Inserted {0} into the database", fp.toString());
        File monthDir = getFileLocation(fp);
        if (!monthDir.exists()) {
            if (!monthDir.mkdirs()) {
                throw new IOException("Unable to create " + monthDir);
            } else {
                LOG.log(Level.FINE, "created dir {0}", monthDir.getPath());
            }
        }
        File dest = new File(monthDir.getAbsolutePath() + "/" + fp.getFileName().toLowerCase());
        copyFile(new File(fp.getAbsolutePath()), dest);
        dest.setLastModified(fp.getShotDate().getTime());
        LOG.log(Level.FINE, "Copied file to {0}", monthDir.getPath());
    }
    
    protected File getFileLocation(Photo fp) {
        return new File(store + getSubfolder(fp.getShotDate()));
    }
    
    protected void handleExistingPhoto(ExistingPhotoException e, FilePhoto fp) {
        if(e.isToBeReplaced()) {
            File stored = getFileLocation(e.getBlocking());
            File destination = getFileLocation(fp);
            stored.renameTo(destination);
            db.updateFileName(fp);
            LOG.log(Level.FINE, "replaced {0} with {1}", new Object[]{stored, fp});
        } else {
            LOG.log(Level.FINE, "Ignored {0} because we had preferable copy", fp);
        }
    }

    public static int getProcessed() {
        synchronized (LOG) {
            return processed;
        }
    }

    private static String getSubfolder(Date shot) {
        SimpleDateFormat sdf = new SimpleDateFormat("/yyyy/MM/");
        return sdf.format(shot);
    }

    private static void copyFile(File sourceFile, File destFile)
            throws IOException {
        if (!sourceFile.exists()) {
            return;
        }
        if (!destFile.exists()) {
            destFile.createNewFile();
        }
        FileChannel source = null;
        FileChannel destination = null;
        source = new FileInputStream(sourceFile).getChannel();
        destination = new FileOutputStream(destFile).getChannel();
        if (destination != null && source != null) {
            destination.transferFrom(source, 0, source.size());
        }
        if (source != null) {
            source.close();
        }
        if (destination != null) {
            destination.close();
        }

    }

}
