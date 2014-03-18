package photodb.photo;

import java.util.Date;
import java.util.logging.Logger;

/**
 * PhotoDbEntry - short description. Detailed description.
 *
 * @author Steffen Schumacher
 * @version 1.0
 */
public class PhotoDbEntry extends Photo {

    private final static Logger LOG = Logger.getLogger(FilePhoto.class.getName());

    protected final int vRes;
    protected final int hRes;
    protected final Date shotDate;
    protected final String camera;
    protected final String fileName;
    protected String fileNameNoExtention;

    public PhotoDbEntry(String fileName, Date shotDate, int vRes, int hRes, String camera) {
        this.vRes = vRes;
        this.hRes = hRes;
        this.shotDate = shotDate;
        this.camera = camera;
        this.fileName = fileName;
        fileNameNoExtention = fileName.substring(fileName.lastIndexOf("."));
    }

    
    
    @Override
    public String toString() {
        return "FilePhoto{" + fileName + "(" + vRes + "x" + hRes + ", shot " + shotDate + ", using " + camera + ")}";
    }
   //<editor-fold defaultstate="collapsed" desc="Implement abstract getters from Photo">
    @Override
    public int getHRes() {
        return hRes;
    }

    @Override
    public int getVRes() {
        return vRes;
    }

    @Override
    public Date getShotDate() {
        return shotDate;
    }

    @Override
    public String getCamera() {
        return camera;
    }

    @Override
    public String getFileName() {
        return fileName;
    }

    @Override
    public String getFileNameNoExtention() {
        return fileNameNoExtention;
    }
    //</editor-fold>
}
