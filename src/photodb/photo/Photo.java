package photodb.photo;

import java.io.File;
import java.io.FileNotFoundException;
import java.util.Date;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Photo - short description.
 * Detailed description.
 * 
 * @author  Steffen Schumacher
 * @version 1.0
 */
public abstract class Photo {
    // Find filename without absolute path, and separate extention.
    private final static Pattern _patFile = Pattern.compile("^(.*[\\/\\\\]|)([^\\/^\\\\]+)\\.([^\\.]+)$");
    
    public abstract int getHRes();
    public abstract int getVRes();
    public abstract Date getShotDate();
    public abstract String getCamera();
    public abstract String getFileName();
    public abstract String getFileNameNoExtention();
    
    public double getAspectRatio() {
        return (double) getHRes() / (double) getVRes();
    }

    public boolean isDuplicateOf(Photo candidate) {
        return isAspectRatioIdentical(candidate) &&
                !isCameraDifferent(candidate) &&
                (isFileNamesSimilar(candidate) ||
                 isShotDateIdentical(candidate) );
    }

    protected boolean isAspectRatioIdentical(Photo candidate) {
        return getAspectRatio() == candidate.getAspectRatio();
    }
    
    protected boolean isFileNamesSimilar(Photo candidate) {
        String us = getFileNameNoExtention().toUpperCase();
        String other = candidate.getFileNameNoExtention().toUpperCase();
        return (us.contains(other) || other.contains(us));
    }
    
    protected boolean isShotDateIdentical(Photo candidate) {
        Date we = getShotDate();
        Date other = candidate.getShotDate();
        return (we != null) && other != null && we.equals(other);
    }
    
    public boolean isCameraDifferent(Photo candidate) {
        String us = getCamera();
        String other = candidate.getCamera();
        return (us != null && other != null && !us.equals(other));
    }
    
    public boolean isPreferredTo(Photo candidate) {
        Date we = getShotDate();
        Date other = candidate.getShotDate();
        if(we != null) {
            //We have a date
            if(other == null || we.before(other)) {
                //He doesn't, or we are older
                return true;
            } else if(we.after(other)) {
                return false;
            }
        } else if(other != null) {  //Only they have a date
            return false;
        }
        //There are either identical dates, or not dates at all
        return getVRes() > candidate.getVRes();
    }
    
        protected Matcher validateFileName(String absPath) throws FileNotFoundException {
        Matcher m = _patFile.matcher(absPath);
        return m;
    }
}
