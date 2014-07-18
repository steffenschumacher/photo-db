/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package photodb.photo;

import java.util.Date;
import javax.xml.bind.annotation.XmlElement;

/**
 *
 * @author ssch
 */
public class SoapPhoto extends Photo {

    @XmlElement()
    private int hRes;
    @XmlElement()
    private int vRes;
    @XmlElement(nillable = false, required = true)
    private Date shotDate;
    @XmlElement(nillable = false, required = true)
    private String camera;
    @XmlElement(nillable = false, required = true)
    private String fileName;
    @XmlElement(nillable = false, required = true)
    private String fileNameNoExtention;
    private boolean eligible;

    public int getHRes() {
        return hRes;
    }

    public void setHRes(int hRes) {
        this.hRes = hRes;
    }

    public int getVRes() {
        return vRes;
    }

    public void setVRes(int vRes) {
        this.vRes = vRes;
    }

    public Date getShotDate() {
        return shotDate;
    }

    public void setShotDate(Date shotDate) {
        this.shotDate = shotDate;
    }

    public String getCamera() {
        return camera;
    }

    public void setCamera(String camera) {
        this.camera = camera;
    }

    public String getFileName() {
        return fileName;
    }

    public void setFileName(String fileName) {
        this.fileName = fileName;
    }

    @Override
    public String getFileNameNoExtention() {
        return fileNameNoExtention;
    }

    public void setFileNameNoExtention(String fileNameNoExtention) {
        this.fileNameNoExtention = fileNameNoExtention;
    }

    public SoapPhoto() {
    }

    public SoapPhoto(int hRes, int vRes, Date shotDate, String camera, String fileName, String fileNameNoExtention) {
        this.hRes = hRes;
        this.vRes = vRes;
        this.shotDate = shotDate;
        this.camera = camera;
        this.fileName = fileName;
        this.fileNameNoExtention = fileNameNoExtention;
    }

    
    @XmlElement(nillable = true, required = false)
    public boolean isEligible() {
        return eligible;
    }

    public void setEligible(boolean isEligible) {
        this.eligible = isEligible;
    }
    
    

    @Override
    public String toString() {
        return "SoapPhoto{" + fileName + "(" + vRes + "x" + hRes + ", shot " + shotDate + ", using " + camera + ")}";
    }

}
