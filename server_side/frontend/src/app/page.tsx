'use client';

import { useState } from 'react';
import ImageUploader from '@/components/ImageUploader';
import BoundingBoxCanvas from '@/components/BoundingBoxCanvas';
import StatsPanel from '@/components/StatsPanel';
import Header from '@/components/Header';
import LiveVideoStream from '@/components/LiveVideoStream';
import { Detection, CountResult } from '@/types';

export default function Home() {
  const [result, setResult] = useState<CountResult | null>(null);
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<CountResult[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  const [liveCount, setLiveCount] = useState(0);

  const handleResult = (newResult: CountResult, imageData: string) => {
    setResult(newResult);
    setOriginalImage(imageData);
    setError(null);
    
    // Add to history
    setHistory(prev => [
      { ...newResult, timestamp: new Date().toISOString() },
      ...prev.slice(0, 9) // Keep last 10 results
    ]);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
    setResult(null);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Header />
      
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Content - Live Stream */}
          <div className="lg:col-span-3 space-y-6">
            {/* Live Video Stream */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl shadow-2xl border border-gray-700/50 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold text-white flex items-center space-x-3">
                  <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></span>
                  <span>Live Camera Feed</span>
                </h2>
              </div>
              
              <LiveVideoStream 
                onCountUpdate={setLiveCount}
                pollInterval={300}
              />
            </div>
            
            {/* Collapsible Upload Section */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700/50 overflow-hidden">
              <button
                onClick={() => setShowUpload(!showUpload)}
                className="w-full px-6 py-4 flex items-center justify-between text-white hover:bg-gray-700/50 transition-colors"
              >
                <span className="flex items-center space-x-3">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <span className="font-semibold">Upload Image for Analysis</span>
                </span>
                <svg 
                  className={`w-5 h-5 transition-transform ${showUpload ? 'rotate-180' : ''}`} 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              
              {showUpload && (
                <div className="px-6 pb-6 space-y-4">
                  <ImageUploader
                    onResult={handleResult}
                    onError={handleError}
                    isLoading={isLoading}
                    setIsLoading={setIsLoading}
                  />
                  
                  {error && (
                    <div className="p-4 bg-red-900/30 border border-red-600 text-red-400 rounded-lg">
                      {error}
                    </div>
                  )}
                  
                  {/* Upload Results */}
                  {isLoading ? (
                    <div className="flex items-center justify-center h-48">
                      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                    </div>
                  ) : result && originalImage ? (
                    <BoundingBoxCanvas
                      imageData={originalImage}
                      detections={result.detections}
                      peopleCount={result.people_count}
                    />
                  ) : null}
                </div>
              )}
            </div>
          </div>
          
          {/* Side Panel - Stats */}
          <div className="lg:col-span-1 space-y-6">
            {/* Live Count Card */}
            <div className="bg-gradient-to-br from-blue-600 to-purple-700 rounded-2xl shadow-xl p-6 text-white">
              <div className="text-sm font-medium opacity-80 mb-1">Live People Count</div>
              <div className="text-5xl font-bold">{liveCount}</div>
              <div className="text-xs opacity-60 mt-2">Real-time detection</div>
            </div>
            
            {/* Stats Panel */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700/50">
              <StatsPanel result={result} history={history} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
