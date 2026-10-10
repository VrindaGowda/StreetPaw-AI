import React, { useState, useEffect } from 'react';
import { Modal, Button, Input, Card, Badge } from '@streetpaw/ui';
import { Camera, MapPin, CheckCircle2, AlertTriangle, ArrowRight, ArrowLeft, Sparkles, RefreshCw, ShieldCheck, Heart } from 'lucide-react';
import { LocationPicker } from './LocationPicker';
import { PawBurstContainer } from './PawBurst';
import { useAuth } from '../context/AuthContext';

export function CreateDogStepperModal({ isOpen, onClose, onSuccess, prefilledData = null }) {
  const { user, token } = useAuth();
  const [currentStep, setCurrentStep] = useState(1);

  // Form State
  const [photoUrl, setPhotoUrl] = useState('');
  const [name, setName] = useState('');
  const [breed, setBreed] = useState('Indian Pariah / Desi');
  const [originalAiBreed, setOriginalAiBreed] = useState('');
  const [breedConfidence, setBreedConfidence] = useState(0);
  const [diseaseName, setDiseaseName] = useState('Normal');
  const [diseaseConfidence, setDiseaseConfidence] = useState(0);
  const [sex, setSex] = useState('unknown');
  const [approxAge, setApproxAge] = useState('2 years');
  const [colourMarkings, setColourMarkings] = useState('Tan & White chest patch');
  const [sterilised, setSterilised] = useState('yes');
  const [earNotch, setEarNotch] = useState(true);
  const [status, setStatus] = useState('Healthy / Sterilized');

  // Location State
  const [locationData, setLocationData] = useState({
    lat: 12.9081,
    lng: 77.5653,
    address: 'DSU Campus Gate 2, Bengaluru',
    area: 'Kudlu Gate / Hosur Road',
    city: 'Bengaluru',
    state: 'Karnataka'
  });

  // Duplicate Check State
  const [isCheckingDuplicate, setIsCheckingDuplicate] = useState(false);
  const [duplicateResult, setDuplicateResult] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  // Submit State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);

  // Synchronize state from prefilledData every time modal opens or scan data updates
  useEffect(() => {
    if (isOpen) {
      setCurrentStep(1);
      setShowCelebration(false);
      setDuplicateResult(null);
      setSelectedCandidate(null);
      setName('');

      if (prefilledData) {
        const incomingPhoto = prefilledData.image_url || prefilledData.image || prefilledData.previewUrl || '';
        const incomingBreed = prefilledData.breed || 'Indian Pariah / Desi';
        const incomingStatus = prefilledData.status || prefilledData.health_status || 'Healthy / Sterilized';
        const incomingDisease = prefilledData.disease || 'Normal';
        const incomingBreedConf = prefilledData.breed_confidence || 0;
        const incomingDiseaseConf = prefilledData.disease_confidence || 0;

        setPhotoUrl(incomingPhoto);
        setBreed(incomingBreed);
        setOriginalAiBreed(prefilledData.breed || '');
        setBreedConfidence(incomingBreedConf);
        setDiseaseName(incomingDisease);
        setDiseaseConfidence(incomingDiseaseConf);
        setStatus(incomingStatus);
      } else {
        setPhotoUrl('');
        setBreed('Indian Pariah / Desi');
        setOriginalAiBreed('');
        setBreedConfidence(0);
        setDiseaseName('Normal');
        setDiseaseConfidence(0);
        setStatus('Healthy / Sterilized');
      }
    }
  }, [isOpen, prefilledData]);

  // Step 3: Run Duplicate Check when entering Review step
  const handleProceedToStep3 = async () => {
    setCurrentStep(3);
    setIsCheckingDuplicate(true);
    setDuplicateResult(null);

    try {
      const res = await fetch('http://localhost:8000/api/dogs/check-duplicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          photo_url: photoUrl,
          breed,
          area: locationData.area || locationData.address,
          colour_markings: colourMarkings
        })
      });
      const data = await res.json();
      setDuplicateResult(data);
      if (data.duplicates_found && data.candidates.length > 0) {
        setSelectedCandidate(data.candidates[0]);
      }
    } catch (e) {
      console.warn('Duplicate check warning:', e);
    } finally {
      setIsCheckingDuplicate(false);
    }
  };

  // Option A: Link sighting to existing candidate
  const handleLinkToExistingCandidate = async (candidate) => {
    if (!token) {
      alert("Please login first to log a sighting.");
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await fetch(`http://localhost:8000/api/dogs/${candidate.public_code || candidate.animal_id}/locations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          lat: locationData.lat,
          lng: locationData.lng,
          address: locationData.address,
          area: locationData.area,
          city: locationData.city,
          state: locationData.state,
          note: 'Sighting linked via Duplicate Check Workflow'
        })
      });

      if (!res.ok) {
        if (res.status === 401) {
          throw new Error('Your login session has expired. Please log in again.');
        }
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to link sighting');
      }

      setShowCelebration(true);
      setTimeout(() => {
        if (onSuccess) onSuccess(candidate.public_code || candidate.animal_id);
        if (onClose) onClose();
      }, 1200);
    } catch (err) {
      console.error(err);
      alert(`Linking sighting failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Option B: Register brand new Dog ID
  const handleRegisterNewDog = async () => {
    if (!token) {
      alert("Please login to register a dog in the central database.");
      return;
    }
    setIsSubmitting(true);
    try {
      // Determine if breed was modified by the human or retained from AI prediction
      const isAiBreed = Boolean(
        originalAiBreed &&
        breed.trim().toLowerCase() === originalAiBreed.trim().toLowerCase()
      );
      const computedBreedSource = isAiBreed ? 'ai' : 'human';

      const res = await fetch('http://localhost:8000/api/dogs/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: name ? name.trim() : undefined,
          species: 'Dog',
          breed: breed.trim() || 'Indian Pariah / Desi',
          breed_source: computedBreedSource,
          sex,
          approx_age: approxAge,
          colour_markings: colourMarkings,
          sterilised,
          ear_notch: earNotch,
          status,
          health_status: status,
          disease_name: diseaseName || 'Normal',
          disease_confidence: parseFloat(diseaseConfidence || 0),
          image_url: photoUrl || 'https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=400&auto=format&fit=crop',
          location: locationData.address || 'Bengaluru',
          location_lat: locationData.lat,
          location_lng: locationData.lng,
          area: locationData.area || locationData.address,
          city: locationData.city || 'Bengaluru',
          state: locationData.state || 'Karnataka'
        })
      });

      if (!res.ok) {
        if (res.status === 401) {
          throw new Error('Your login session has expired. Please log in again.');
        }
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to register dog');
      }

      const data = await res.json();
      setShowCelebration(true);
      setTimeout(() => {
        if (onSuccess) onSuccess(data.public_code || data.animal_id);
        if (onClose) onClose();
      }, 1200);
    } catch (err) {
      console.error('Registration error:', err);
      alert(`Registration failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isBreedAiRetained = Boolean(
    originalAiBreed &&
    breed.trim().toLowerCase() === originalAiBreed.trim().toLowerCase()
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Register Stray Dog ID" maxWidth="640px">
      <div className="stepper-modal-container">
        {/* Step Indicator Bar */}
        <div className="stepper-indicator-bar">
          <div className={`step-dot ${currentStep >= 1 ? 'active' : ''}`}>1. Details</div>
          <div className="step-line" />
          <div className={`step-dot ${currentStep >= 2 ? 'active' : ''}`}>2. Location</div>
          <div className="step-line" />
          <div className={`step-dot ${currentStep >= 3 ? 'active' : ''}`}>3. Review</div>
        </div>

        {/* STEP 1: DETAILS (WITH PHOTO) */}
        {currentStep === 1 && (
          <div className="step-content">
            <h4 className="step-heading">Step 1: Animal Details & Identification</h4>
            <p className="step-sub">Review physical characteristics and sterilization tags. You can edit any field before registering.</p>

            {/* Photo preview attached with details - No raw URLs */}
            {photoUrl ? (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                padding: '12px 16px',
                background: 'rgba(15, 23, 42, 0.7)',
                borderRadius: 'var(--radius-lg, 12px)',
                border: '1px solid var(--border-subtle, rgba(255,255,255,0.1))'
              }}>
                <img
                  src={photoUrl}
                  alt="Stray preview"
                  style={{
                    width: '84px',
                    height: '84px',
                    borderRadius: '10px',
                    objectFit: 'cover',
                    border: '2px solid var(--primary-coral, #ff7e67)',
                    flexShrink: 0
                  }}
                />
                <div>
                  <div style={{ fontWeight: 800, fontSize: '0.95rem', color: '#ffffff' }}>
                    Stray Dog Photo
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted, #94a3b8)', marginTop: '2px' }}>
                    Biometric image linked to this animal record for Re-ID visual recognition.
                  </div>
                </div>
              </div>
            ) : null}

            <div className="form-grid-2">
              <div>
                <label className="field-label">Pet / Stray Name (Optional)</label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Bruno or Desi Pack Leader" />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label className="field-label" style={{ margin: 0 }}>Breed Classification</label>
                  {originalAiBreed ? (
                    isBreedAiRetained ? (
                      <Badge variant="brand">
                        🤖 AI PREDICTED {breedConfidence > 0 ? `(${Math.round(breedConfidence)}%)` : ''}
                      </Badge>
                    ) : (
                      <Badge variant="uncertain">
                        ✏️ USER EDITED (Human Choice)
                      </Badge>
                    )
                  ) : (
                    <Badge variant="normal">
                      👤 MANUAL ENTRY
                    </Badge>
                  )}
                </div>
                <Input
                  list="breed-options-list"
                  value={breed}
                  onChange={(e) => setBreed(e.target.value)}
                  placeholder="e.g. Indian Pariah / Desi, Beagle, Pug, Labrador..."
                  required
                />
                <datalist id="breed-options-list">
                  <option value="Indian Pariah / Desi" />
                  <option value="Street Mongrel" />
                  <option value="Indie Pariah Mix" />
                  <option value="Beagle" />
                  <option value="Boxer" />
                  <option value="Bulldog" />
                  <option value="Dachshund" />
                  <option value="German Shepherd" />
                  <option value="Golden Retriever" />
                  <option value="Labrador Retriever" />
                  <option value="Pomeranian" />
                  <option value="Poodle" />
                  <option value="Pug" />
                  <option value="Rottweiler" />
                  <option value="Siberian Husky" />
                  <option value="Indian Hound Mix" />
                </datalist>
              </div>

              <div>
                <label className="field-label">Sex</label>
                <select className="custom-select" value={sex} onChange={(e) => setSex(e.target.value)}>
                  <option value="male">Male ♂</option>
                  <option value="female">Female ♀</option>
                  <option value="unknown">Unknown</option>
                </select>
              </div>

              <div>
                <label className="field-label">Approximate Age</label>
                <Input value={approxAge} onChange={(e) => setApproxAge(e.target.value)} placeholder="e.g. 2 years" />
              </div>

              <div className="col-span-2">
                <label className="field-label">Colour & Distinguishing Markings</label>
                <Input value={colourMarkings} onChange={(e) => setColourMarkings(e.target.value)} placeholder="e.g. Tan coat, white chest patch, black muzzle" />
              </div>

              <div>
                <label className="field-label">Sterilization Status (ABC Program)</label>
                <select className="custom-select" value={sterilised} onChange={(e) => setSterilised(e.target.value)}>
                  <option value="yes">Sterilized (Yes)</option>
                  <option value="no">Not Sterilized (No)</option>
                  <option value="unknown">Unknown</option>
                </select>
              </div>

              <div>
                <label className="field-label">Ear Notch Present?</label>
                <select className="custom-select" value={earNotch ? 'yes' : 'no'} onChange={(e) => setEarNotch(e.target.value === 'yes')}>
                  <option value="yes">Yes (Right/Left Ear Notched)</option>
                  <option value="no">No Notch Visible</option>
                </select>
              </div>

              <div className="col-span-2">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label className="field-label" style={{ margin: 0 }}>Health & Vaccination Status</label>
                  {diseaseName && diseaseName !== 'Normal' && (
                    <Badge variant="critical">
                      🚨 AI Flagged: {diseaseName} {diseaseConfidence > 0 ? `(${Math.round(diseaseConfidence)}%)` : ''}
                    </Badge>
                  )}
                </div>
                <select className="custom-select" value={status} onChange={(e) => setStatus(e.target.value)}>
                  <option value="Healthy / Sterilized">Healthy / Sterilized</option>
                  <option value="Under Medical Care">Under Medical Care</option>
                  <option value="Vaccinated">Vaccinated</option>
                  <option value="Needs Attention">Needs Attention</option>
                </select>
              </div>
            </div>

            <div className="stepper-actions mt-4">
              <Button variant="ghost" onClick={onClose}>Cancel</Button>
              <Button variant="emerald" icon={ArrowRight} onClick={() => setCurrentStep(2)}>
                Next: Set Location
              </Button>
            </div>
          </div>
        )}

        {/* STEP 2: LOCATION */}
        {currentStep === 2 && (
          <div className="step-content">
            <h4 className="step-heading">Step 2: Sighting Location</h4>
            <p className="step-sub">Use GPS, search address, or drop a pin on the map.</p>

            <LocationPicker
              initialLocation={{
                lat: locationData.lat,
                lng: locationData.lng,
                address: locationData.address,
                area: locationData.area,
                city: locationData.city,
                state: locationData.state
              }}
              onSelectLocation={(loc) => {
                setLocationData(loc);
                handleProceedToStep3();
              }}
              onCancel={() => setCurrentStep(1)}
              confirmLabel="Next: Review & Duplicate Check"
            />
          </div>
        )}

        {/* STEP 3: REVIEW & DUPLICATE CHECK */}
        {currentStep === 3 && (
          <div className="step-content">
            <h4 className="step-heading">Step 3: Human-in-the-Loop Duplicate Verification</h4>

            {isCheckingDuplicate ? (
              <div className="checking-duplicate-spinner">
                <RefreshCw size={32} className="spin" color="var(--primary-coral)" />
                <p>Running Re-ID embeddings & similarity matching against central database...</p>
              </div>
            ) : showCelebration ? (
              <div className="celebration-box">
                <PawBurstContainer type="paw">
                  <Sparkles size={48} color="#10b981" />
                </PawBurstContainer>
                <h3 className="text-xl font-bold text-emerald-400 mt-2">Dog ID Created Successfully!</h3>
                <p className="text-muted text-sm">Registered into Central Digital Animal Registry & NGO Network.</p>
              </div>
            ) : (
              <div className="review-step-wrapper">
                {duplicateResult?.duplicates_found && selectedCandidate ? (
                  <Card variant="glow" className="duplicate-alert-card">
                    <div className="duplicate-card-header">
                      <AlertTriangle size={24} color="#f59e0b" />
                      <div>
                        <h4 className="font-bold text-amber-300">Possible Existing Match Found!</h4>
                        <p className="text-xs text-muted">This animal matches candidate {selectedCandidate.public_code} with {Math.round(selectedCandidate.similarity_score * 100)}% similarity score.</p>
                      </div>
                    </div>

                    <div className="candidate-preview-box">
                      <img src={selectedCandidate.image_url} alt="Candidate" className="candidate-thumb" />
                      <div>
                        <div className="font-bold text-coral-400">{selectedCandidate.public_code} ({selectedCandidate.animal_id})</div>
                        <div className="text-xs text-white">{selectedCandidate.name} • {selectedCandidate.breed}</div>
                        <div className="text-xs text-muted">📍 {selectedCandidate.location}</div>
                      </div>
                    </div>

                    <div className="duplicate-choice-buttons">
                      <Button
                        variant="primary"
                        icon={CheckCircle2}
                        loading={isSubmitting}
                        onClick={() => handleLinkToExistingCandidate(selectedCandidate)}
                      >
                        Yes, Same Dog! (Add Sighting to {selectedCandidate.public_code})
                      </Button>

                      <Button
                        variant="emerald"
                        loading={isSubmitting}
                        onClick={handleRegisterNewDog}
                      >
                        No, Register Brand New Dog ID
                      </Button>
                    </div>
                  </Card>
                ) : (
                  <Card variant="glass" className="no-duplicate-card">
                    <Badge variant="emerald">✓ Zero Duplicates Detected</Badge>
                    <h4 className="font-bold text-lg text-white mt-2">Ready to Register Brand New Dog ID</h4>
                    <p className="text-muted text-sm mt-1">
                      {breed} • {locationData.address}
                    </p>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '8px', lineHeight: '1.5' }}>
                      <span>Classification Source: </span>
                      {isBreedAiRetained ? (
                        <span style={{ color: '#60a5fa', fontWeight: 600 }}>🤖 AI Predicted ({Math.round(breedConfidence)}%)</span>
                      ) : (
                        <span style={{ color: '#facc15', fontWeight: 600 }}>✏️ User Edited (Human Verified)</span>
                      )}
                      {diseaseName && diseaseName !== 'Normal' && (
                        <div>Health Note: <span style={{ color: '#f87171', fontWeight: 600 }}>{diseaseName}</span></div>
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
                      <Button
                        variant="secondary"
                        icon={ArrowLeft}
                        onClick={() => setCurrentStep(2)}
                      >
                        Back
                      </Button>
                      <Button
                        variant="emerald"
                        icon={Sparkles}
                        size="lg"
                        style={{ flex: 1 }}
                        loading={isSubmitting}
                        onClick={handleRegisterNewDog}
                      >
                        Register into Database
                      </Button>
                    </div>
                  </Card>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
