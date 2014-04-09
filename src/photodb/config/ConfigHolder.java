package photodb.config;

import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 *
 * @author ssch
 */
class ConfigHolder {

    private Config INSTANCE = null;
    private final Semaphore sem = new Semaphore(1);

    public Config getINSTANCE() throws NotInitializedException {
        if (INSTANCE == null) {
            try {
                if (sem.tryAcquire(1, TimeUnit.SECONDS)) {
                    if (INSTANCE == null) {
                        throw new NotInitializedException(this);
                    } else {
                        //We'll release the semaphore since config was initialized
                        //by the time we got the semaphore..
                        sem.release();  
                    }
                } else {
                    Logger.getLogger(ConfigHolder.class.getName()).log(Level.SEVERE, 
                            "Unable to initialize config with expected time");
                }
            } catch (InterruptedException ex) {
                Logger.getLogger(ConfigHolder.class.getName()).log(Level.SEVERE, null, ex);
            }
        }
        return INSTANCE;
    }

    protected void instantiateConfig(Config c) {
        if (INSTANCE != null) {
            Logger.getLogger(ConfigHolder.class.getName()).log(Level.SEVERE,
                    "Bug - instance should be null when attempting instantiation");
        }
        INSTANCE = c;
        sem.release();
    }

}
