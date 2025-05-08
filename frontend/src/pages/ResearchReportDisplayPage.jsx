import React from 'react';
import ResearchDirectionsReportView from '../components/comparison/ResearchDirectionsReportView';

// Sample data for testing
const sampleResearchDirections = [
  {
    id: 'dir1',
    title: 'Advancements in Quantum Entanglement Communication',
    summary: 'Exploring the latest breakthroughs in using quantum entanglement for secure and instantaneous communication across vast distances. This includes theoretical models and experimental verifications.',
    papers: [
      { id: 'paper1a', title: 'Experimental Validation of Long-Distance Quantum Communication', summary: 'This paper details an experiment successfully demonstrating quantum-entangled communication over 100km.' },
      { id: 'paper1b', title: 'Theoretical Limits of Entanglement-Based Bandwidth', summary: 'A theoretical exploration of the maximum achievable data transfer rates using current quantum entanglement theories.' },
    ],
  },
  {
    id: 'dir2',
    title: 'AI-Powered Drug Discovery for Neurodegenerative Diseases',
    summary: 'Leveraging artificial intelligence and machine learning models to accelerate the identification and validation of novel drug candidates for diseases like Alzheimer\'s and Parkinson\'s.',
    papers: [
      { id: 'paper2a', title: 'Machine Learning Predicts Novel Drug Targets for Alzheimer\'s', summary: 'Utilizes a deep learning model to analyze genomic data and predict potential new drug targets.' },
      { id: 'paper2b', title: 'High-Throughput Screening of Compounds Using AI', summary: 'Describes an automated system guided by AI for rapidly screening thousands of chemical compounds.' },
      { id: 'paper2c', title: 'Ethical Considerations in AI Drug Discovery', summary: 'Discusses the ethical implications and biases in using AI for medical research and drug development.' },
    ],
  },
  {
    id: 'dir3',
    title: 'Sustainable Urban Agriculture Technologies',
    summary: 'Developing and implementing innovative technologies for sustainable food production within urban environments, focusing on vertical farming, hydroponics, and closed-loop systems.',
    papers: [
      { id: 'paper3a', title: 'Optimizing LED Lighting for Vertical Farms', summary: 'Investigates the impact of different LED light spectrums on crop yield and nutritional value in vertical farming setups.' },
    ],
  },
  {
    id: 'dir4',
    title: 'The Role of Microbiome in Mental Health',
    summary: 'Investigating the complex interactions between the gut microbiome and brain function, and its potential impact on mental health disorders such as depression and anxiety.',
    papers: [
      { id: 'paper4a', title: 'Gut-Brain Axis: A New Frontier for Psychiatry', summary: 'Reviews the current understanding of the gut-brain axis and its implications for psychiatric conditions.' },
      { id: 'paper4b', title: 'Probiotics as a Potential Treatment for Anxiety', summary: 'A clinical trial examining the efficacy of specific probiotic strains in reducing anxiety symptoms.' },
    ],
  },
];

const ResearchReportDisplayPage = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      {/* <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Research Directions Report</h1>
        <p className="text-gray-600">Comparison of generated research directions.</p>
      </header> */}
      <ResearchDirectionsReportView researchDirections={sampleResearchDirections} />
    </div>
  );
};

export default ResearchReportDisplayPage; 