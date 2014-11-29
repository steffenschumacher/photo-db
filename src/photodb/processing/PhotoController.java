/*
 *  
 *  TDC A/S CONFIDENTIAL
 *  __________________
 *  
 *   [2004] - [2013] TDC A/S, Operations department 
 *   All Rights Reserved.
 *  
 *  NOTICE:  All information contained herein is, and remains
 *  the property of TDC A/S and its suppliers, if any.
 *  The intellectual and technical concepts contained herein are
 *  proprietary to TDC A/S and its suppliers and may be covered
 *  by Danish and Foreign Patents, patents in process, and are 
 *  protected by trade secret or copyright law.
 *  Dissemination of this information or reproduction of this 
 *  material is strictly forbidden unless prior written 
 *  permission is obtained from TDC A/S.
 *  
 */
package photodb.processing;

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
import photodb.db.ExistingPhotoException;
import photodb.photo.FilePhoto;
import photodb.photo.Photo;

/**
 * PhotoControler - short description. Detailed description.
 *
 * @author Steffen Schumacher <steff@tdc.dk>
 * @CVS $Id$
 * @version 1.0
 */
public class PhotoController {

    private final static Logger LOG = Logger.getLogger(PhotoController.class.getName());
    private final String store;
    private final Database db;

    public PhotoController(String store, Database db) {
        this.store = store;
        this.db = db;
    }

    public PhotoController(final String store) throws SQLException {
        this.store = store;
        this.db = initDb(store);
    }
    
    protected static Database initDb(String store) throws SQLException {
        return new Database(store + "/photo.db");
    }
    
    public boolean exists(Photo filephoto) {
        try {
            db.insert(filephoto);
            db.delete(filephoto);
            return false;
        } catch (ExistingPhotoException e) {
            return true;
        }
    }
    
    public boolean isDesired(Photo filephoto) {
        try {
            db.insert(filephoto);
            db.delete(filephoto);
            return true;
        } catch (ExistingPhotoException e) {
            return e.isToBeReplaced();
        }
    }
    
    

    public void insert(FilePhoto fp) throws ExistingPhotoException, IOException {
        File sourceFile = new File(fp.getAbsolutePath());
        if (sourceFile.exists()) {
            FileChannel source = new FileInputStream(sourceFile).getChannel();
            insert(fp, source);
            if (source != null) {
                source.close();
            }
        }        
    }
    
    public void insert(Photo fp, FileChannel source) throws ExistingPhotoException, IOException {
        db.insert(fp);
        LOG.log(Level.FINE, "Inserted {0} into the database", fp.toString());
        File dest = establishDestinationPath(fp);
        copyChannel(source, dest);
        dest.setLastModified(fp.getShotDate().getTime());
        LOG.log(Level.FINE, "Copied file to {0}", dest.getPath());
    }

    public File establishDestinationPath(Photo fp) throws IOException {
        File monthDir = getFileLocation(fp);
        if (!monthDir.exists()) {
            if (!monthDir.mkdirs()) {
                throw new IOException("Unable to create " + monthDir);
            } else {
                LOG.log(Level.FINE, "created dir {0}", monthDir.getPath());
            }
        }
        File dest = new File(monthDir.getAbsolutePath() + "/" + fp.getFileName());
        return dest;
    }

    protected File getFileLocation(Photo fp) {
        return new File(store + getSubfolder(fp.getShotDate()));
    }

    protected void handleExistingPhoto(ExistingPhotoException e, FilePhoto fp) {
        if (e.isToBeReplaced()) {
            File stored = getFileLocation(e.getBlockingPhoto());
            File destination = getFileLocation(fp);
            stored.renameTo(destination);
            db.updateFileName(fp);
            LOG.log(Level.FINE, "replaced {0} with {1}", new Object[]{stored, fp});
        } else {
            LOG.log(Level.FINE, "Ignored {0} because we had preferable copy", fp);
        }
    }

    private String getSubfolder(Date shot) {
        SimpleDateFormat sdf = new SimpleDateFormat("/yyyy/MM/");
        return sdf.format(shot);
    }

    private void copyChannel(FileChannel source, File destFile) throws IOException {
        if (!destFile.exists()) {
            destFile.createNewFile();
        }
        FileChannel destination = new FileOutputStream(destFile).getChannel();
        if (destination != null && source != null) {
            destination.transferFrom(source, 0, source.size());
        }
        if (destination != null) {
            destination.close();
        }
    }

    public void close() {
        if(db != null) {
            db.close();
        }
    }
}
