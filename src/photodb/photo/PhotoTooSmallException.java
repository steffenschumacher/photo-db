
package photodb.photo;

/**
 *
 * @author Steffen Schumacher
 */
public class PhotoTooSmallException extends Exception {

    /**
     * Creates a new instance of <code>PhotoTooSmallException</code> without
     * detail message.
     */
    public PhotoTooSmallException() {
    }

    /**
     * Constructs an instance of <code>PhotoTooSmallException</code> with the
     * specified detail message.
     *
     * @param msg the detail message.
     */
    public PhotoTooSmallException(String msg) {
        super(msg);
    }
}
