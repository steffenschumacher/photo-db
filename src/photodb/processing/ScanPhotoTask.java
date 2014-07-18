package photodb.processing;

import com.drew.imaging.ImageProcessingException;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.sql.SQLException;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.xml.datatype.DatatypeConfigurationException;
import javax.xml.ws.BindingProvider;
import photodb.db.Database;
import photodb.db.ExistingPhotoException;
import photodb.photo.FilePhoto;
import photodb.photo.PhotoTooSmallException;
import photodb.wsclient.ExistingPhotoWSException;
import photodb.wsclient.PhotoDBWS;
import photodb.wsclient.PhotoDBWS_Service;
import photodb.wsclient.SoapPhoto;

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
    private static PhotoDBWS s_port;
    private static boolean isLocal;

    public static void initForLocalDb(String store) {
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

    public static void initForRemoteDb(String wsdlUrl) {
        s_store = System.getProperty("java.io.tmpdir") + File.pathSeparator
                + "tmp-photodb-" + System.currentTimeMillis() + ".db";
        try {
            s_db = new Database(s_store);
        } catch (SQLException ex) {
            LOG.log(Level.SEVERE, "Unable to init temporary database", ex);
            System.exit(0);
        }
        PhotoDBWS_Service service = new PhotoDBWS_Service();
        s_port = service.getPhotoDBWSPort();
        BindingProvider bp = (BindingProvider) s_port;
        if (wsdlUrl == null) {
            wsdlUrl = "http://localhost:8084/PhotoDbWS/PhotoDBWS";
        }
        bp.getRequestContext().put(
                BindingProvider.ENDPOINT_ADDRESS_PROPERTY,
                wsdlUrl);
        isLocal = false;

    }

    public static void cleanup() {
        if (isLocal) {
            return;
        }
        s_db.close();
        File tmpDb = new File(s_store);
        tmpDb.deleteOnExit();
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
            super.insert(fp);
        } else {

            SoapPhoto sp = toSoapPhoto(fp);
            if(!isUploadEligible(fp)) { 
                LOG.log(Level.INFO, "Ingoring {0} as it is a duplicate of a photo already processed in this scan", fp.toString());
            } else if (!s_port.isUploadEligible(sp)) {
                LOG.log(Level.INFO, "Ingoring {0} as it already existed remotely", fp.toString());
            } else {
                LOG.log(Level.FINE, "Preparing to upload {0}", fp.toString());
                long start = System.currentTimeMillis();
                byte[] data = Files.readAllBytes(Paths.get(fp.getAbsolutePath()));
                try {
                    s_port.add(sp, data);
                    LOG.log(Level.INFO, "Uploaded {0} in {1} ms", new Object[]{fp.toString(), (System.currentTimeMillis() - start)});
                } catch (ExistingPhotoWSException ex) {
                    LOG.log(Level.SEVERE,
                            "Attempt to insert photo failed("
                            + fp.getAbsolutePath() + ")", ex);
                }
            }
        }
    }

    
    /**
     * isUploadEligible checks if the photo exists in the temporary database,
     * which contains the photos uploaded thus far. 
     * If the photo exists, it is checked if the blocking photo is eligible to
     * be replaced with the provided one.
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

    private static SoapPhoto toSoapPhoto(FilePhoto fp) {
        SoapPhoto SoapPhoto = new SoapPhoto();
        SoapPhoto.setCamera(fp.getCamera());
        SoapPhoto.setFileName(fp.getFileName());
        SoapPhoto.setFileNameNoExtention(fp.getFileNameNoExtention());
        SoapPhoto.setHRes(fp.getHRes());
        SoapPhoto.setVRes(fp.getVRes());
        try {
            SoapPhoto.setShotDate(fp.getShotDateXML());
        } catch (DatatypeConfigurationException ex) {
            LOG.log(Level.SEVERE, "Funky exception", ex);
        }
        return SoapPhoto;
    }

    public static int getProcessed() {
        synchronized (LOG) {
            return processed;
        }
    }

}
