package photodb.processing;

import com.drew.imaging.ImageProcessingException;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.channels.FileChannel;
import java.sql.SQLException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.logging.Level;
import java.util.logging.Logger;
import photodb.db.Database;
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
    private static final String store = "/Users/ssch/PhotoDb";
    private static Database db;
    static {
        try {
            db = new Database(store+"/photo.db");
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
            if(fp.getShotDate() != null && db.findByDate(fp.getShotDate()) == null) {
                db.insert(fp);
                LOG.log(Level.FINE, "Inserted {0} into the database", fp.toString());
                File monthDir = new File(store+getSubfolder(fp.getShotDate()));
                if(!monthDir.exists()) {
                    if(!monthDir.mkdirs()) {
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
