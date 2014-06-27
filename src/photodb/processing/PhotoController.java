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
import java.io.IOException;
import java.util.logging.Level;
import photodb.db.Database;
import photodb.db.ExistingPhotoException;
import photodb.photo.FilePhoto;

/**
 * PhotoControler - short description.
 * Detailed description.
 * 
 * @author  Steffen Schumacher <steff@tdc.dk>
 * @CVS     $Id$
 * @version 1.0
 */
public class PhotoController {
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
}
