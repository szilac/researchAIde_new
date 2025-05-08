import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ProgressIndicator from '../components/form/ProgressIndicator';
import StepWrapper from '../components/form/StepWrapper';
import Button from '../components/form/Button';
import LLMSelector from '../components/form/LLMSelector';
import InputField from '../components/form/InputField';
import TextareaField from '../components/form/TextareaField';
import { SessionService } from '../services/SessionService';
import usePersistentState from '../hooks/usePersistentState';

const TOTAL_STEPS = 2;
const stepNames = ['Select LLM', 'Enter Topic'];
const STEP_STORAGE_KEY = 'researchSetupStep';
const DATA_STORAGE_KEY = 'researchSetupData';

function ResearchSetupPage() {
  const [currentStep, setCurrentStep] = usePersistentState(STEP_STORAGE_KEY, 1);
  const [formData, setFormData] = usePersistentState(DATA_STORAGE_KEY, {
    llmProvider: '',
    llmModelId: '',
    researchArea: '',
    researchTopic: '',
    researchContext: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);   // For API/general errors
  const [errors, setErrors] = useState({}); // For field-specific validation errors
  const navigate = useNavigate();

  // Clear specific field error on change
  const handleFormChange = (field, value) => {
    setFormData(prevData => ({ ...prevData, [field]: value }));
    if (errors[field]) {
      setErrors(prevErrors => ({ ...prevErrors, [field]: null }));
    }
    setSubmitError(null); 
  };
  const handleLLMSelect = (modelId, provider) => {
    setFormData(prevData => ({ ...prevData, llmModelId: modelId, llmProvider: provider }));
    if (errors.llmModelId) { // Clear LLM error on selection
      setErrors(prevErrors => ({ ...prevErrors, llmModelId: null }));
    }
    setSubmitError(null); 
  };

  // Validation Logic
  const validateStep = (step) => {
    const newErrors = {};
    if (step === 1) {
      if (!formData.llmModelId) {
        newErrors.llmModelId = 'Please select an LLM model.';
      }
    }
    if (step === 2) {
      if (!formData.researchTopic.trim()) {
        newErrors.researchTopic = 'Focused research topic cannot be empty.';
      }
      // Add more validation for step 2 if needed (e.g., researchArea)
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0; // Return true if no errors
  };

  // --- Navigation handlers ---
  const nextStep = () => {
    if (!validateStep(currentStep)) return; // Use validateStep
    
    setSubmitError(null); 
    if (currentStep < TOTAL_STEPS) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    setErrors({}); // Clear errors when going back
    setSubmitError(null); 
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleFinalSubmit = async () => {
    if (!validateStep(currentStep)) return; // Use validateStep for final step

    setIsSubmitting(true);
    setSubmitError(null);
    setErrors({}); // Clear field errors before submit
    console.log('Submitting Form Data:', formData);

    try {
      const createdSession = await SessionService.createSession(formData);
      console.log('API call successful:', createdSession);
      alert(`Session created successfully! (ID: ${createdSession?.sessionId || 'N/A'})`);
      
      // Clear persistent state on successful submission
      localStorage.removeItem(STEP_STORAGE_KEY);
      localStorage.removeItem(DATA_STORAGE_KEY);

      navigate('/');
    } catch (error) {
      console.error('API call failed:', error);
      setSubmitError(error.message || 'An unexpected error occurred.');
    } finally {
      setIsSubmitting(false);
    }
  };
  // --- End Navigation Handlers ---

  return (
    <div className="max-w-2xl mx-auto p-4">
      <ProgressIndicator
        currentStep={currentStep}
        totalSteps={TOTAL_STEPS}
        stepNames={stepNames}
      />

      {/* Step 1: LLM Selection */}
      {currentStep === 1 && (
        <StepWrapper title={stepNames[0]}>
          <LLMSelector
            selectedModelId={formData.llmModelId}
            onModelSelect={handleLLMSelect}
            error={errors.llmModelId} // Pass down error
          />
        </StepWrapper>
      )}

      {/* Step 2: Topic Entry */}
      {currentStep === 2 && (
        <StepWrapper title={stepNames[1]}>
          <InputField
            id="researchArea"
            label="General Research Area"
            value={formData.researchArea}
            onChange={(e) => handleFormChange('researchArea', e.target.value)}
            placeholder="e.g., Artificial Intelligence, Renewable Energy, Cancer Biology"
            error={errors.researchArea} // Pass down error
          />
          <InputField
            id="researchTopic"
            label="Focused Research Topic / Question"
            value={formData.researchTopic}
            onChange={(e) => handleFormChange('researchTopic', e.target.value)}
            placeholder="e.g., Using LLMs for code generation, Perovskite solar cell efficiency, CAR-T cell therapy side effects"
            required
            error={errors.researchTopic} // Pass down error
          />
          <TextareaField
            id="researchContext"
            label="Additional Context (Optional)"
            value={formData.researchContext}
            onChange={(e) => handleFormChange('researchContext', e.target.value)}
            placeholder="Provide any background information, specific goals, or constraints relevant to your research topic..."
            rows={5}
            error={errors.researchContext} // Pass down error
          />
        </StepWrapper>
      )}

      {/* General Submission Error Display */}
      {submitError && (
        <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded" role="alert">
          <p className="font-bold">Error:</p>
          <p>{submitError}</p>
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-6">
        <Button 
          onClick={prevStep} 
          disabled={currentStep === 1 || isSubmitting}
          variant="secondary"
        >
          Previous
        </Button>
        
        {currentStep < TOTAL_STEPS ? (
          <Button onClick={nextStep} disabled={isSubmitting}>
            Next
          </Button>
        ) : (
          <Button 
            onClick={handleFinalSubmit} 
            variant="primary" 
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Starting Session...' : 'Start Session'}
          </Button>
        )}
      </div>
    </div>
  );
}

export default ResearchSetupPage;
