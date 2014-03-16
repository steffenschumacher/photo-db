package photodb.photo;

import com.drew.metadata.Directory;
import com.drew.metadata.exif.ExifSubIFDDirectory;
import com.drew.metadata.jpeg.JpegDirectory;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Set;
import photodb.photo.dir.InteroperabilityDirectory;

/**
 * MetaDir - short description. Detailed description.
 *
 * @author Steffen Schumacher
 * @version 1.0
 */
public class MetaDir {

    private static final HashMap<Class<? extends Directory>, MetaDir> map = new HashMap<>();

    static {
        map.put(JpegDirectory.class,
                new MetaDir(    //dates, vRes, hRes, make, model
                        new int[]{},
                        new int[]{JpegDirectory.TAG_JPEG_IMAGE_WIDTH},
                        new int[]{JpegDirectory.TAG_JPEG_IMAGE_HEIGHT},
                        new int[]{},
                        new int[]{}
                ));
        map.put(ExifSubIFDDirectory.class,
                new MetaDir(
                        new int[]{},
                        new int[]{ExifSubIFDDirectory.TAG_EXIF_IMAGE_WIDTH},
                        new int[]{ExifSubIFDDirectory.TAG_EXIF_IMAGE_HEIGHT},
                        new int[]{},
                        new int[]{}
                ));
        map.put(InteroperabilityDirectory.class,
                new MetaDir(
                        new int[]{},
                        new int[]{InteroperabilityDirectory.TAG_INTOP_IMAGE_WIDTH},
                        new int[]{InteroperabilityDirectory.TAG_INTOP_IMAGE_HEIGHT},
                        new int[]{},
                        new int[]{}
                ));
    }
    
    public static ArrayList<Class<? extends Directory> > getDirectories() {
        ArrayList<Class<? extends Directory> > retval = new ArrayList<>();
        retval.addAll(map.keySet());
        return retval;
    }

    public static MetaDir getTagsFor(Class<? extends Directory> dir) {
        return map.get(dir);
    }
    
    private final int[] dateTags;
    private final int[] vResTags;
    private final int[] hResTags;
    private final int[] makeTags;
    private final int[] modelTags;

    protected MetaDir(int[] dateTags, int[] vResTags, int[] hResTags, int[] makeTags, int[] modelTags) {
        this.dateTags = dateTags;
        this.vResTags = vResTags;
        this.hResTags = hResTags;
        this.makeTags = makeTags;
        this.modelTags = modelTags;
    }

    public int[] getDateTags() {
        return dateTags;
    }

    public int[] getvResTags() {
        return vResTags;
    }

    public int[] gethResTags() {
        return hResTags;
    }

    public int[] getMakeTags() {
        return makeTags;
    }

    public int[] getModelTags() {
        return modelTags;
    }

}
