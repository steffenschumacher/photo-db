package photodb.photo;

import com.drew.imaging.ImageMetadataReader;
import com.drew.imaging.ImageProcessingException;
import com.drew.metadata.Directory;
import com.drew.metadata.Metadata;
import com.drew.metadata.MetadataException;
import com.drew.metadata.Tag;
import java.awt.Point;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Date;
import java.util.Iterator;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.imageio.ImageIO;

/**
 * FilePhoto - short description. Detailed description.
 *
 * @author Steffen Schumacher
 * @version 1.0
 */
public class FilePhoto extends Photo {

    private final static Logger LOG = Logger.getLogger(FilePhoto.class.getName());
    // Find filename without absolute path, and separate extention.
    private final static Pattern _patFile = Pattern.compile("^(.*[\\/\\\\]|)([^\\/^\\\\]+)\\.([^\\.]+)$");
    //<editor-fold defaultstate="collapsed" desc="static reflection methods for calling parameter-specific methods">
    private final static Method getDeclaredSearchMethod(String method) {
        try {
            return FilePhoto.class.getDeclaredMethod(method, new Class[]{Directory.class});
            
        } catch (NoSuchMethodException | SecurityException ex) {
            LOG.log(Level.SEVERE, "Code Error! Unable to get method: " + method, ex);
            return null;
        }
        
    }
    private final static Method _metFindResolution = getDeclaredSearchMethod("findResolutionInDir");
    private final static Method _metFindShotDate = getDeclaredSearchMethod("findShotDateInDir");
    private final static Method _metFindCamera = getDeclaredSearchMethod("findCameraInDir");
    
    //</editor-fold>


    protected final int vRes;
    protected final int hRes;
    protected final Date shotDate;
    protected final String camera;
    protected final String fileName;
    protected final String fileNameNoExtention;
    protected final String absPath;
    protected ArrayList<Class<? extends Directory>> directories;

    public FilePhoto(String absPath) throws FileNotFoundException, ImageProcessingException, IOException {
        boolean failed = false;
        this.absPath = absPath;

        Matcher m = validateFileName(absPath);
        fileNameNoExtention = m.group(2);
        fileName = fileNameNoExtention + "." + m.group(3);
        Metadata metadata = ImageMetadataReader.readMetadata(new File(absPath));
        directories = MetaDir.getDirectories();
        //logMetadata(metadata);
        Point res = findResolution(metadata);
        vRes = (int) res.getY();
        hRes = (int) res.getX();
        camera = findCamera(metadata);
        shotDate = findShotDate(metadata);
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

    //<editor-fold defaultstate="collapsed" desc="Helper methods for parsing metadata">
    private void logMetadata(final Metadata md) {
        for (Directory directory : md.getDirectories()) {
            for (Tag tag : directory.getTags()) {
                LOG.log(Level.FINE, "In {0}:\t({1}){2}",
                        new Object[]{directory.getName(), tag.getTagType(), tag});
            }
        }
    }

    private Date findShotDate(final Metadata md) {
        try {
            return (Date)findDataInDirectoriesFor(_metFindShotDate, md);
        } catch (NullPointerException e) {
            LOG.log(Level.FINE, "{0} for {1}", new Object[]{e.getMessage(), absPath});
            return null;
        }
    }

    private String findCamera(final Metadata md) {
        try {
            return (String)findDataInDirectoriesFor(_metFindCamera, md);
        } catch (NullPointerException e) {
            LOG.log(Level.FINE, "{0} for {1}", new Object[]{e.getMessage(), absPath});
            return null;
        }
        
    }

    private Point findResolution(final Metadata md) {

        try {
            return (Point)findDataInDirectoriesFor(_metFindResolution, md);
        } catch (NullPointerException e) {
            LOG.log(Level.FINE, "{0} for {1}", new Object[]{e.getMessage(), absPath});
        }
        try {
            BufferedImage read = ImageIO.read(new File(absPath));
            return new Point(read.getWidth(), read.getHeight());
        } catch (IOException ex) {
            LOG.log(Level.SEVERE, "Unable to read image for resolution", ex);
            return new Point(0, 0);
        }
    }

    private Point findResolutionInDir(final Directory dir) throws NullPointerException {
        MetaDir md = MetaDir.getTagsFor(dir.getClass());
        for (int i = 0; i < md.getvResTags().length; i++) {
            int vResTag = md.getvResTags()[i];
            int hResTag = md.gethResTags()[i];
            try {
                return new Point(dir.getInt(vResTag), dir.getInt(hResTag));
            } catch (MetadataException ex) {
                LOG.log(Level.FINER, "Found " + dir.getClass().getSimpleName() + ", but no resolution inside, in " + absPath, ex);
            }
        }
        throw new NullPointerException("Didn't find resolution in " + dir.getClass().getSimpleName());
    }

    private Date findShotDateInDir(final Directory dir) throws NullPointerException {
        MetaDir md = MetaDir.getTagsFor(dir.getClass());
        for (int i = 0; i < md.getDateTags().length; i++) {
            int dateTag = md.getDateTags()[i];
            return dir.getDate(dateTag);
        }
        throw new NullPointerException("Didn't find shot date in " + dir.getClass().getSimpleName());
    }
    
    private String findCameraInDir(final Directory dir) throws NullPointerException {
        MetaDir md = MetaDir.getTagsFor(dir.getClass());
        for (int i = 0; i < md.getModelTags().length; i++) {
            int modelTag = md.getModelTags()[i];
            return dir.getString(modelTag);
        }
        throw new NullPointerException("Didn't find camera in " + dir.getClass().getSimpleName());
    }
    
    private Object findDataInDirectoriesFor(Method m, Metadata md) {
        Iterator<Class<? extends Directory>> dirIter = directories.iterator();
        while (dirIter.hasNext()) {
            Class<? extends Directory> dir = dirIter.next();
            if (md.containsDirectory(dir)) {
                try {
                    Object retval = m.invoke(this, new Object[]{md.getDirectory(dir)});
                    LOG.log(Level.FINEST, "Successfully retrieved data using {0} in {1} for {2}", 
                            new Object[]{m.getName(), dir.getSimpleName(), absPath});
                    return retval;
                } catch (NullPointerException e) {
                    LOG.log(Level.FINEST, "{0} for {1}", new Object[]{e.getMessage(), absPath});
                } catch (IllegalAccessException | IllegalArgumentException ex) {
                    LOG.log(Level.SEVERE, "Reflection error", ex);
                    return null;
                } catch(InvocationTargetException ite) {
                    if(!(ite.getCause() instanceof NullPointerException)) {
                        LOG.log(Level.SEVERE, "Unexpected exception thrown from reflected method", ite.getCause());
                    }
                }
            } else {
                dirIter.remove();
                LOG.log(Level.FINEST, "Removing {0} from list of dirs for {1}", new Object[]{dir.getSimpleName(), absPath});
            }
        }
        throw new NullPointerException("Didn't find data with method: " + m.getName());
    }

    private Matcher validateFileName(String absPath) throws FileNotFoundException {

        File f = new File(absPath);
        Matcher m = _patFile.matcher(absPath);

        if (!m.find()) {
            throw new FileNotFoundException("Unable to parse filenames from " + absPath);
        }
        if (!f.isFile()) {
            throw new FileNotFoundException("Appears not to be a file: " + absPath);
        }
        if (!f.canRead()) {
            throw new FileNotFoundException("Cannot read from file: " + absPath);
        }
        return m;
    }
    //</editor-fold>
}
