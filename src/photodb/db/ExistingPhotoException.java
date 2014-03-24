package photodb.db;

import java.sql.SQLException;
import photodb.photo.Photo;

/**
 *
 * @author Steffen Schumacher
 */
public class ExistingPhotoException extends SQLException {
    private final Photo blocking;
    private final boolean toBeReplaced;
    /**
     * Creates a new instance of <code>ExistingPhotoException</code> without
     * detail message.
     * @param blocker
     * @param attempted
     */
    public ExistingPhotoException(Photo blocker, Photo attempted) {
        super("Couldn't insert " + attempted + ", due to existing " + blocker);
        this.blocking = blocker;
        toBeReplaced = (!blocker.getFileName().toLowerCase().startsWith("img_") && 
                attempted.getFileName().toLowerCase().startsWith("img_"));
    }

    public Photo getBlocking() {
        return blocking;
    }

    public boolean isToBeReplaced() {
        return toBeReplaced;
    }
    
    
}
