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

    private final static Logger LOG = Logger.getLogger(ScanPhotoTask.class.getName());
    private final String store;
    private final Database db;

    public PhotoController(String store, Database db) {
        this.store = store;
        this.db = db;
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
        FileChannel source = new FileInputStream(sourceFile).getChannel();
        FileChannel destination = new FileOutputStream(destFile).getChannel();
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
