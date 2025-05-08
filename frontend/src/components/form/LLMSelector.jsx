import React from 'react';

// Placeholder data - replace with actual data fetching later
const llmOptions = [
  // {
  //   provider: 'OpenAI',
  //   models: [
  //     { id: 'gpt-4', name: 'GPT-4' },
  //     { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
  //   ],
  // },gemini-2.5-flash-preview-04-17
  {
    provider: 'Google',
    models: [
      { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' },
      { id: 'gemini-2.0-flash-lite', name: 'Gemini 2.0 Flash Lite' },
      { id: 'gemini-2.5-flash-preview-04-17', name: 'Gemini 2.5 Flash Preview' },
    ],
  },
  // {
  //   provider: 'Anthropic',
  //   models: [
  //     { id: 'claude-3-opus', name: 'Claude 3 Opus' },
  //     { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet' },
  //   ],
  // },
  // Add Ollama/other providers later
];

const LLMSelector = ({ selectedModelId, onModelSelect, error }) => {
  return (
    <div className="space-y-6">
      {llmOptions.map((providerData) => (
        <div key={providerData.provider} className="p-4 border border-gray-200 rounded-md">
          <h3 className="text-lg font-medium text-gray-900 mb-3">{providerData.provider}</h3>
          <div className="space-y-2">
            {providerData.models.map((model) => (
              <label key={model.id} className="flex items-center p-2 rounded-md hover:bg-gray-50">
                <input
                  type="radio"
                  name="llmModel"
                  value={model.id}
                  checked={selectedModelId === model.id}
                  onChange={() => onModelSelect(model.id, providerData.provider)} // Pass ID and provider
                  className="h-4 w-4 text-indigo-600 border-gray-300 focus:ring-indigo-500 mr-3"
                />
                <span className="text-sm text-gray-700">{model.name}</span>
              </label>
            ))}
          </div>
        </div>
      ))}
      {error && (
        <p className="mt-2 text-xs text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

export default LLMSelector; 