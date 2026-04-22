import React from 'react'
import { ModelId } from '../../types/types'

interface ModelSelectorProps {
  currentModel: ModelId
  onSelectModel: (model: ModelId) => void
}

const ModelSelector: React.FC<ModelSelectorProps> = ({ currentModel, onSelectModel }) => {
  const models = [
    { id: ModelId.GPT_5_4, label: 'GPT 5.4' },
    { id: ModelId.PERPLEXITY, label: 'Perplexity' },
  ]

  return (
    <div className="flex justify-center w-full py-4 bg-transparent absolute top-10 left-0 right-0 z-10">
      <div className="bg-white/80 backdrop-blur-md border border-gray-200 p-1 rounded-full shadow-sm flex items-center space-x-1">
        {models.map(model => (
          <button
            key={model.id}
            onClick={() => onSelectModel(model.id)}
            className={`px-4 py-1.5 text-sm font-medium rounded-full transition-all duration-200 ease-in-out ${
              currentModel === model.id
                ? 'bg-gray-900 text-white shadow-md'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-900'
            }`}
          >
            {model.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default ModelSelector
