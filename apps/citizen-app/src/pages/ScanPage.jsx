import React, { useState, useRef } from 'react';
import {
  Camera, Upload, RefreshCw, CheckCircle2, AlertCircle, Download,
  Sparkles, Activity, ZoomIn, ZoomOut, Lock, Info, Plus, PawPrint,
  Heart, Stethoscope, Layers, FileText, ChevronRight, RotateCcw, MessageSquare
} from 'lucide-react';
import { Card, Button, Badge, Skeleton, Modal, Input } from '@streetpaw/ui';
import { PawBurstContainer } from '../components/PawBurst';
import { PawlyMascot } from '../components/PawlyMascot';
import { CameraModal } from '../components/CameraModal';
import { CreateDogStepperModal } from '../components/CreateDogStepperModal';
import { useAuth } from '../context/AuthContext';

export function ScanPage({ setActivePage }) {
  const { user, token } = useAuth();
  const fileInputRef = useRef(null);

  // Photo state
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isZoomed, setIsZoomed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Guided 3-Step Scan state
  const [cachedDetection, setCachedDetection] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzingStep, setAnalyzingStep] = useState(null); // 1 | 2 | 3
  const [step1Done, setStep1Done] = useState(false);
  const [step2Done, setStep2Done] = useState(false);
  const [step3Done, setStep3Done] = useState(false);
  const [scanError, setScanError] = useState(null);

  // HITL Save Modal
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Handle Photo Select / Drag & Drop
  const handleFileSelect = (file) => {
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      resetScanState();
    }
  };

  const handleCameraCapture = (file, url) => {
    setSelectedFile(file);
    setPreviewUrl(url);
    resetScanState();
  };

  const resetScanState = () => {
    setCachedDetection(null);
    setStep1Done(false);
    setStep2Done(false);
    setStep3Done(false);
    setScanError(null);
    setIsZoomed(false);
    setSaveSuccess(false);
  };

  const handleClearPhoto = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    resetScanState();
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Helper: Fetch or return cached AI detection from POST /api/detect
  const fetchOrGetDetection = async () => {
    if (cachedDetection) return cachedDetection;

    const formData = new FormData();
    if (selectedFile) {
      formData.append('file', selectedFile);
    } else if (previewUrl) {
      // Create blob from preview object URL if sample image used
      try {
        const res = await fetch(previewUrl);
        const blob = await res.blob();
        formData.append('file', blob, 'scan_photo.jpg');
      } catch (e) {
        console.error('Blob conversion error:', e);
      }
    }

    try {
      const response = await fetch('http://localhost:8000/api/detect', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('AI Detection service currently busy. Please try again.');
      }

      const data = await response.json();
      const det = data.detections && data.detections[0] ? data.detections[0] : null;
      setCachedDetection(det);
      return det;
    } catch (err) {
      setScanError(err.message || 'Failed to connect to AI engine.');
      throw err;
    }
  };

  // Guided Button 1 Action: What animal is this?
  const handleStep1 = async () => {
    if (!previewUrl || isAnalyzing) return;
    setIsAnalyzing(true);
    setAnalyzingStep(1);
    setScanError(null);

    try {
      const det = await fetchOrGetDetection();
      setStep1Done(true);
    } catch (e) {
      console.error('Step 1 error:', e);
    } finally {
      setIsAnalyzing(false);
      setAnalyzingStep(null);
    }
  };

  // Guided Button 2 Action: What breed is it?
  const handleStep2 = async () => {
    if (!previewUrl || !step1Done || isAnalyzing) return;
    setIsAnalyzing(true);
    setAnalyzingStep(2);
    setScanError(null);

    try {
      await fetchOrGetDetection();
      setStep2Done(true);
    } catch (e) {
      console.error('Step 2 error:', e);
    } finally {
      setIsAnalyzing(false);
      setAnalyzingStep(null);
    }
  };

  // Guided Button 3 Action: Any health concern?
  const handleStep3 = async () => {
    if (!previewUrl || !step1Done || isAnalyzing) return;
    setIsAnalyzing(true);
    setAnalyzingStep(3);
    setScanError(null);

    try {
      await fetchOrGetDetection();
      setStep3Done(true);
    } catch (e) {
      console.error('Step 3 error:', e);
    } finally {
      setIsAnalyzing(false);
      setAnalyzingStep(null);
    }
  };

  // Extracted values from cached detection
  const species = cachedDetection?.species || '';
  const isDog = Boolean(species && species.toLowerCase() === 'dog');
  const confidence = cachedDetection?.confidence ?? 0;
  const breed = isDog
    ? (cachedDetection?.breed === 'Indian breed' ? 'Indian Pariah / Indie' : (cachedDetection?.breed || 'Indian Pariah / Indie'))
    : 'Not applicable';
  const breedConf = isDog ? (cachedDetection?.breed_confidence ?? 0) : 0;
  const disease = isDog ? (cachedDetection?.disease || 'Normal / No visible disease') : 'Not analyzed by dog disease model';
  const diseaseConf = isDog ? (cachedDetection?.disease_confidence ?? 0) : 0;
  const diseaseStatus = isDog ? (cachedDetection?.disease_status || 'normal') : 'not_applicable';

  // Current scan prefill payload for Dog Registry
  const currentScanData = (cachedDetection && isDog) ? {
    image_url: cachedDetection.roi_crop || previewUrl,
    image: cachedDetection.roi_crop || previewUrl,
    previewUrl: previewUrl,
    species: 'Dog',
    breed: cachedDetection.breed === 'Indian breed'
      ? 'Indian Pariah / Desi'
      : (cachedDetection.breed || 'Indian Pariah / Desi'),
    breed_confidence: cachedDetection.breed_confidence || 0,
    disease: cachedDetection.disease || 'Normal',
    disease_confidence: cachedDetection.disease_confidence || 0,
    disease_status: cachedDetection.disease_status || 'normal',
    status: (cachedDetection.disease_status === 'disease_detected')
      ? 'Under Medical Care'
      : 'Healthy / Sterilized',
    health_status: (cachedDetection.disease_status === 'disease_detected')
      ? 'Under Medical Care'
      : 'Healthy / Sterilized',
  } : null;

  // Download PDF Report Helper
  const handleDownloadPdf = () => {
    window.print();
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* 1. TOP PARLEY MASCOT BANNER */}
      <div style={{
        padding: '20px 28px',
        borderRadius: 'var(--radius-xl)',
        background: 'linear-gradient(135deg, rgba(255,158,128,0.12) 0%, rgba(205,184,255,0.12) 50%, rgba(189,235,221,0.12) 100%)',
        border: '1px solid var(--border-medium)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '20px',
        flexWrap: 'wrap'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <PawlyMascot mood={scanError ? 'confused' : step3Done ? 'happy' : 'idle'} size={68} />
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, margin: 0 }}>
              Show me a photo and ask me anything 🐾
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', margin: '4px 0 0' }}>
              Guided 3-step Stray Dog Vision Engine. Fast, friendly, and honest AI estimates.
            </p>
          </div>
        </div>

        <Badge variant="brand">STEP-BY-STEP AI SCANNER</Badge>
      </div>

      {/* 2. MAIN TWO-COLUMN LAYOUT */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
        gap: '32px',
        alignItems: 'start'
      }}>
        
        {/* LEFT COLUMN: UPLOAD CARD + 3 BIG GUIDED BUTTONS */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <Card variant="glass" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 800, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Camera color="var(--primary-coral)" size={20} /> Photo Upload & Preview
            </h3>

            {!previewUrl ? (
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) handleFileSelect(e.dataTransfer.files[0]);
                }}
                onClick={() => fileInputRef.current && fileInputRef.current.click()}
                style={{
                  padding: '48px 24px',
                  border: `2px dashed ${isDragging ? 'var(--primary-coral)' : 'var(--border-medium)'}`,
                  borderRadius: 'var(--radius-lg)',
                  textAlign: 'center',
                  background: isDragging ? 'rgba(255,126,103,0.1)' : 'rgba(15, 21, 35, 0.4)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <Upload size={40} color="var(--primary-coral)" style={{ marginBottom: '12px' }} />
                <div style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '4px' }}>Drag & drop stray photo here</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>Supports JPG, PNG, WEBP files</div>
                
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                  <Button variant="primary" size="sm" icon={Upload} onClick={(e) => { e.stopPropagation(); fileInputRef.current.click(); }}>
                    Choose photo
                  </Button>
                  <Button variant="secondary" size="sm" icon={Camera} onClick={(e) => { e.stopPropagation(); setIsCameraOpen(true); }}>
                    Use camera
                  </Button>
                </div>
                <input ref={fileInputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => e.target.files[0] && handleFileSelect(e.target.files[0])} />
              </div>
            ) : (
              <div style={{ position: 'relative', width: '100%', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                <img
                  src={previewUrl}
                  alt="Stray photo preview"
                  style={{
                    width: '100%',
                    height: '280px',
                    objectFit: 'cover',
                    borderRadius: 'var(--radius-lg)',
                    transform: isZoomed ? 'scale(1.5)' : 'scale(1)',
                    transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)'
                  }}
                />

                {/* Soft Sweeping-Light Scan Animation Overlay */}
                {isAnalyzing && (
                  <div style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0) 100%)',
                    animation: 'sp-sweeping-light 1.5s infinite linear',
                    pointerEvents: 'none'
                  }} />
                )}

                {/* Drawn Detection Bounding Box on Photo */}
                {step1Done && species && (
                  <div style={{
                    position: 'absolute',
                    top: '15%',
                    left: '20%',
                    width: '60%',
                    height: '65%',
                    border: `3px solid ${isDog ? '#22c55e' : '#f59e0b'}`,
                    borderRadius: '8px',
                    boxShadow: `0 0 15px ${isDog ? 'rgba(34, 197, 94, 0.5)' : 'rgba(245, 158, 11, 0.5)'}`,
                    pointerEvents: 'none'
                  }}>
                    <span style={{
                      position: 'absolute',
                      top: '-26px',
                      left: '-3px',
                      background: isDog ? '#22c55e' : '#f59e0b',
                      color: '#ffffff',
                      fontSize: '0.75rem',
                      fontWeight: 800,
                      padding: '2px 10px',
                      borderRadius: '4px'
                    }}>
                      {species}
                    </span>
                  </div>
                )}

                {/* Single Zoom Icon Toggle (Shown only after Button 3 or when enabled) */}
                {(step3Done || isZoomed) && (
                  <button
                    onClick={() => setIsZoomed(!isZoomed)}
                    title={isZoomed ? 'Zoom Out' : 'Zoom In'}
                    style={{
                      position: 'absolute',
                      bottom: '12px',
                      right: '12px',
                      background: 'rgba(15, 23, 42, 0.85)',
                      border: '1px solid var(--border-medium)',
                      borderRadius: '50%',
                      width: '38px',
                      height: '38px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#fff',
                      cursor: 'pointer'
                    }}
                  >
                    {isZoomed ? <ZoomOut size={18} /> : <ZoomIn size={18} />}
                  </button>
                )}

                <button
                  onClick={handleClearPhoto}
                  style={{
                    position: 'absolute',
                    top: '12px',
                    right: '12px',
                    background: 'rgba(239, 68, 68, 0.85)',
                    border: 'none',
                    borderRadius: '50%',
                    width: '32px',
                    height: '32px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    cursor: 'pointer'
                  }}
                >
                  <RotateCcw size={16} />
                </button>
              </div>
            )}
          </Card>

          {/* THREE BIG ICON-LED GUIDED BUTTONS */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            
            {/* BUTTON 1: What animal is this? */}
            <PawBurstContainer type="paw">
              <button
                onClick={handleStep1}
                disabled={!previewUrl || isAnalyzing}
                style={{
                  width: '100%',
                  padding: '18px 24px',
                  borderRadius: 'var(--radius-xl)',
                  background: step1Done
                    ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(16, 185, 129, 0.3))'
                    : 'linear-gradient(135deg, #ff7e67 0%, #ff5733 100%)',
                  border: step1Done ? '1px solid #22c55e' : 'none',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: previewUrl && !isAnalyzing ? 'pointer' : 'not-allowed',
                  opacity: !previewUrl ? 0.6 : 1,
                  boxShadow: 'var(--shadow-glow)',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  {step1Done ? <CheckCircle2 size={24} color="#4ade80" /> : <PawPrint size={24} />}
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>1. What animal is this?</div>
                    <div style={{ fontSize: '0.775rem', opacity: 0.9 }}>YOLOv8 Species & Quadruped Detection</div>
                  </div>
                </div>
                {analyzingStep === 1 ? (
                  <Skeleton width="24px" height="24px" borderRadius="50%" />
                ) : step1Done ? (
                  <Badge variant="emerald">CONFIRMED</Badge>
                ) : (
                  <ChevronRight size={20} />
                )}
              </button>
            </PawBurstContainer>

            {/* BUTTON 2: What breed is it? (Locked until Button 1 confirms dog) */}
            <PawBurstContainer type="sparkle">
              <button
                onClick={handleStep2}
                disabled={!step1Done || !isDog || isAnalyzing}
                title={!step1Done ? 'Find out what animal it is first' : !isDog ? `Dog-specific analysis (Not applicable for ${species || 'non-dog'})` : ''}
                style={{
                  width: '100%',
                  padding: '18px 24px',
                  borderRadius: 'var(--radius-xl)',
                  background: step2Done
                    ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(16, 185, 129, 0.3))'
                    : step1Done && isDog
                    ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)'
                    : 'rgba(30, 41, 59, 0.6)',
                  border: step2Done ? '1px solid #22c55e' : '1px solid var(--border-subtle)',
                  color: step1Done && isDog ? '#ffffff' : 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: step1Done && isDog && !isAnalyzing ? 'pointer' : 'not-allowed',
                  opacity: !step1Done || !isDog ? 0.65 : 1,
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  {!step1Done || !isDog ? (
                    <Lock size={22} color="var(--text-muted)" />
                  ) : step2Done ? (
                    <CheckCircle2 size={24} color="#4ade80" />
                  ) : (
                    <Layers size={24} />
                  )}
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>2. What breed is it?</div>
                    <div style={{ fontSize: '0.775rem', opacity: 0.9 }}>
                      {!step1Done ? 'Find out what animal it is first' : !isDog ? `Locked — Not applicable for ${species}` : 'EfficientNet-B3 Breed Neural Classifier'}
                    </div>
                  </div>
                </div>
                {analyzingStep === 2 ? (
                  <Skeleton width="24px" height="24px" borderRadius="50%" />
                ) : step2Done ? (
                  <Badge variant="emerald">DONE</Badge>
                ) : (
                  <ChevronRight size={20} />
                )}
              </button>
            </PawBurstContainer>

            {/* BUTTON 3: Any health concern? (Locked until Button 1 confirms dog) */}
            <PawBurstContainer type="sparkle">
              <button
                onClick={handleStep3}
                disabled={!step1Done || !isDog || isAnalyzing}
                title={!step1Done ? 'Find out what animal it is first' : !isDog ? `Dog-specific analysis (Not applicable for ${species || 'non-dog'})` : ''}
                style={{
                  width: '100%',
                  padding: '18px 24px',
                  borderRadius: 'var(--radius-xl)',
                  background: step3Done
                    ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(16, 185, 129, 0.3))'
                    : step1Done && isDog
                    ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                    : 'rgba(30, 41, 59, 0.6)',
                  border: step3Done ? '1px solid #22c55e' : '1px solid var(--border-subtle)',
                  color: step1Done && isDog ? '#ffffff' : 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: step1Done && isDog && !isAnalyzing ? 'pointer' : 'not-allowed',
                  opacity: !step1Done || !isDog ? 0.65 : 1,
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  {!step1Done || !isDog ? (
                    <Lock size={22} color="var(--text-muted)" />
                  ) : step3Done ? (
                    <CheckCircle2 size={24} color="#4ade80" />
                  ) : (
                    <Stethoscope size={24} />
                  )}
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>3. Any health concern?</div>
                    <div style={{ fontSize: '0.775rem', opacity: 0.9 }}>
                      {!step1Done ? 'Find out what animal it is first' : !isDog ? `Locked — Not applicable for ${species}` : 'Skin Disease & Infection Risk Profiling'}
                    </div>
                  </div>
                </div>
                {analyzingStep === 3 ? (
                  <Skeleton width="24px" height="24px" borderRadius="50%" />
                ) : step3Done ? (
                  <Badge variant="emerald">DONE</Badge>
                ) : (
                  <ChevronRight size={20} />
                )}
              </button>
            </PawBurstContainer>
          </div>
        </div>

        {/* RIGHT COLUMN: ONE RESULT CARD PER BUTTON (ANIMATES IN ONLY AFTER USED) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Default Empty State when No Photo / Buttons Untapped */}
          {!step1Done && !isAnalyzing && (
            <Card variant="glass" style={{ padding: '40px 24px', textAlign: 'center' }}>
              <Info size={40} color="var(--primary-coral)" style={{ marginBottom: '12px' }} />
              <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '6px' }}>Ready to Scan Stray Photo</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', maxWidth: '340px', margin: '0 auto' }}>
                Upload or capture a photo, then tap button 1 <strong>"What animal is this?"</strong> to start the guided scan.
              </p>
            </Card>
          )}

          {scanError && (
            <Card variant="critical">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <AlertCircle size={24} color="#f87171" />
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 800, color: '#f87171' }}>AI Engine Service Error</h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>{scanError}</p>
                </div>
              </div>
            </Card>
          )}

          {/* CARD 1: ANIMAL RESULT CARD (Animates in after Button 1) */}
          {step1Done && (
            <Card variant="glass" style={{ animation: 'sp-fade-in 400ms var(--ease-calm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <Badge variant={isDog ? 'brand' : 'critical'}>
                  {isDog ? '• DOG DETECTED' : `• ${species.toUpperCase()} DETECTED`}
                </Badge>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  Confidence: {confidence}%
                </span>
              </div>

              {isDog ? (
                <div>
                  <h3 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-emerald)', marginBottom: '8px' }}>
                    Canine Species Confirmed 🐾
                  </h3>
                  <div style={{ height: '6px', width: '100%', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginBottom: '12px' }}>
                    <div style={{ height: '100%', width: `${confidence}%`, background: 'var(--accent-emerald)' }} />
                  </div>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', margin: 0 }}>
                    Buttons 2 and 3 are now unlocked! Tap button 2 to classify breed or button 3 for health profiling.
                  </p>
                </div>
              ) : (
                <div>
                  <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f59e0b', marginBottom: '8px' }}>
                    {species} Detected ({confidence}%)
                  </h3>
                  <div style={{ height: '6px', width: '100%', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginBottom: '12px' }}>
                    <div style={{ height: '100%', width: `${Math.min(confidence, 100)}%`, background: '#f59e0b' }} />
                  </div>
                  <div style={{ padding: '12px 16px', background: 'rgba(15, 23, 42, 0.7)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', marginBottom: '8px' }}>
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: '1.5', margin: 0 }}>
                      StreetPaw's breed classification and skin disease profiling models are specialized for stray canines. Breed and disease analyses are locked and not applicable for {species}.
                    </p>
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* CARD 2: BREED RESULT CARD (Animates in after Button 2) */}
          {step2Done && isDog && (
            <Card variant="glass" style={{ animation: 'sp-fade-in 400ms var(--ease-calm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <Badge variant="brand">• BREED CLASSIFICATION</Badge>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  Top Match: {breedConf}%
                </span>
              </div>

              <h3 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ffffff', marginBottom: '12px' }}>
                {breed}
              </h3>

              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.775rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Secondary possibilities:</span>
                {cachedDetection?.breed_top3 && cachedDetection.breed_top3.length > 1 ? (
                  cachedDetection.breed_top3.slice(1).map((item, idx) => (
                    <Badge key={idx} variant="normal">
                      {idx === 0 ? '🥈' : '🥉'} {item.breed} ({typeof item.confidence === 'number' ? item.confidence.toFixed(1) : item.confidence}%)
                    </Badge>
                  ))
                ) : (
                  <Badge variant="normal">None detected</Badge>
                )}
              </div>
            </Card>
          )}

          {/* CARD 3: HEALTH RESULT CARD (Animates in after Button 3) */}
          {step3Done && isDog && (
            <Card variant="glass" style={{ animation: 'sp-fade-in 400ms var(--ease-calm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <Badge variant={diseaseStatus === 'normal' ? 'emerald' : 'critical'}>
                  {diseaseStatus === 'normal' ? '• NO VISIBLE CONCERN' : '• MEDICAL ATTENTION SUGGESTED'}
                </Badge>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  AI Confidence: {diseaseConf}%
                </span>
              </div>

              <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: diseaseStatus === 'normal' ? '#4ade80' : '#f87171', marginBottom: '8px' }}>
                {diseaseStatus === 'normal' ? 'Healthy / No Visible Skin Lesions' : `Possible skin issue: ${disease}`}
              </h3>

              <div style={{ padding: '12px 16px', background: 'rgba(15, 23, 42, 0.8)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', marginBottom: '12px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary-coral)', marginBottom: '4px' }}>
                  💡 First-Aid Action Tip:
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0, lineHeight: '1.4' }}>
                  {diseaseStatus === 'normal'
                    ? 'Keep the dog hydrated and provide shade. Consider registering them into our Digital Animal Registry.'
                    : 'Clean scraped area with warm water. Use our "Report as in distress" button to dispatch a local NGO vet squad.'}
                </p>
              </div>

              {/* Permanent Disclaimer Line */}
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', borderTop: '1px solid var(--border-subtle)', pt: '8px', marginTop: '8px' }}>
                * This is a preliminary AI estimate, not a diagnosis. Please consult a qualified veterinarian.
              </div>
            </Card>
          )}

          {/* Low Confidence honest advisory banner (< 60%) */}
          {(step1Done || step2Done || step3Done) && (confidence < 60 || breedConf < 60) && (
            <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.15)', border: '1px solid rgba(245, 158, 11, 0.4)', color: '#fbbf24', fontSize: '0.85rem', lineHeight: '1.4' }}>
              ⚠️ AI Confidence is under 60%. We suggest retaking the photo in better light, closer, and side-on for higher precision.
            </div>
          )}

          {/* WHAT NEXT ROW (Shown after results arrive) */}
          {step1Done && isDog && (
            <Card variant="glow" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#ffffff', marginBottom: '14px' }}>
                What next with this scan result?
              </div>

              {saveSuccess && (
                <div style={{ padding: '10px 14px', background: 'rgba(34, 197, 94, 0.2)', border: '1px solid #22c55e', color: '#4ade80', borderRadius: '8px', fontSize: '0.85rem', marginBottom: '12px' }}>
                  ✓ Successfully saved stray dog profile & AI scan health event to registry!
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <Button
                  variant="brand"
                  size="sm"
                  icon={MessageSquare}
                  onClick={() => {
                    window.dispatchEvent(new CustomEvent('streetpaw:open-pawly-chat', {
                      detail: {
                        scan_result: {
                          species: species,
                          breed: breed,
                          health_status: disease,
                          disease_status: diseaseStatus,
                          confidence: confidence
                        }
                      }
                    }));
                  }}
                >
                  Ask Pawly about this scan
                </Button>
                <Button
                  variant="emerald"
                  size="sm"
                  icon={Plus}
                  disabled={!isDog}
                  onClick={() => {
                    if (!user) {
                      if (setActivePage) setActivePage('login');
                      return;
                    }
                    setIsSaveModalOpen(true);
                  }}
                >
                  Save to Dog Registry
                </Button>
                <Button variant="primary" size="sm" icon={AlertCircle} onClick={() => setActivePage && setActivePage('distress')}>
                  Report as in distress
                </Button>
                <Button variant="secondary" size="sm" icon={Download} onClick={handleDownloadPdf}>
                  Download report (PDF)
                </Button>
              </div>
            </Card>
          )}

        </div>
      </div>

      {/* 4-Step Registration Stepper Modal with Scan-Specific Prefilled Data */}
      {isSaveModalOpen && (
        <CreateDogStepperModal
          isOpen={isSaveModalOpen}
          onClose={() => setIsSaveModalOpen(false)}
          prefilledData={currentScanData}
          onSuccess={(code) => {
            setSaveSuccess(true);
            setIsSaveModalOpen(false);
          }}
        />
      )}

      {/* CAMERA MODAL */}
      {isCameraOpen && (
        <CameraModal isOpen={isCameraOpen} onClose={() => setIsCameraOpen(false)} onCapture={handleCameraCapture} />
      )}
    </div>
  );
}
