package photodb.photo.dir;

import java.util.HashMap;

/**
 * InteroperabilityDirectory - short description.
 * Detailed description.
 * 
 * @author  Steffen Schumacher
 * @version 1.0
 */
public class InteroperabilityDirectory extends com.drew.metadata.Directory {
    public static final int TAG_INTOP_IMAGE_WIDTH = 4097;
    public static final int TAG_INTOP_IMAGE_HEIGHT = 4098;
    
    private final static HashMap<Integer, String> _tagNameMap = new HashMap<>();
    static {
        _tagNameMap.put(1, "Interoperability Index");
        _tagNameMap.put(2, "Interoperability Version");
        _tagNameMap.put(TAG_INTOP_IMAGE_WIDTH, "Related Image Width");
        _tagNameMap.put(TAG_INTOP_IMAGE_HEIGHT, "Related Image Length");
        
    }
    @Override
    public String getName() {
        return "Interoperability";
    }

    @Override
    protected HashMap<Integer, String> getTagNameMap() {
        
        throw new UnsupportedOperationException("Not supported yet."); //To change body of generated methods, choose Tools | Templates.
    }

}
