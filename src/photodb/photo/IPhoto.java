package photodb.photo;

import java.io.FileInputStream;

/**
 * IPhoto - short description.
 * Detailed description.
 * 
 * @author  Steffen Schumacher
 * @version 1.0
 */
public interface IPhoto {
    public boolean isDuplicateOf(IPhoto candidate);
    public boolean isPreferredTo(IPhoto candidate);
    public FileInputStream getInputStream();
    
}
