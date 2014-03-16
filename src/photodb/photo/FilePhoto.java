package photodb.photo;

import com.drew.imaging.ImageMetadataReader;
import com.drew.imaging.ImageProcessingException;
import com.drew.metadata.Directory;
import com.drew.metadata.Metadata;
import com.drew.metadata.MetadataException;
import com.drew.metadata.Tag;
import com.drew.metadata.exif.ExifSubIFDDirectory;
import com.drew.metadata.jfif.JfifDirectory;
import com.drew.metadata.jpeg.JpegDirectory;
import java.awt.Point;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.imageio.ImageIO;
import photodb.photo.dir.InteroperabilityDirectory;

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
        logMetadata(metadata);
        Point res = findResolution(metadata);
        vRes = (int) res.getY();
        hRes = (int) res.getX();
        camera = findCamera(metadata);
        shotDate = findShotDate(metadata);
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

        return null;
    }

    private String findCamera(final Metadata md) {
        return null;
    }

    private Point findResolution(final Metadata md) {
        for (Class<? extends Directory> dir : directories) {
            if (md.containsDirectory(dir)) {
                try {
                    return findResolutionInDir(md.getDirectory(dir));
                } catch (NullPointerException e) {
                    LOG.log(Level.FINEST, "{0} for {1}", new Object[]{e.getMessage(), absPath});
                }
            }
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
