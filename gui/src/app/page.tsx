'use client';

import { useState } from 'react';
import ImageUploader from '@/components/ImageUploader';
import BoundingBoxCanvas from '@/components/BoundingBoxCanvas';
import StatsPanel from '@/components/StatsPanel';
import Header from '@/components/Header';
import { Detection, CountResult } from '@/types';

export default function Home() {
  const [result, setResult] = useState<CountResult | null>(null);
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<CountResult[]>([]);

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
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header />
      
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Upload */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-white">
                Upload Image
              </h2>
              <ImageUploader
                onResult={handleResult}
                onError={handleError}
                isLoading={isLoading}
                setIsLoading={setIsLoading}
              />
              
              {error && (
                <div className="mt-4 p-4 bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-400 rounded-lg">
                  {error}
                </div>
              )}
            </div>
            
            {/* Stats Panel */}
            <div className="mt-6">
              <StatsPanel result={result} history={history} />
            </div>
          </div>
          
          {/* Right Panel - Results */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-white">
                Detection Results
              </h2>
              
              {isLoading ? (
                <div className="flex items-center justify-center h-96">
                  <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
                </div>
              ) : result && originalImage ? (
                <BoundingBoxCanvas
                  imageData={originalImage}
                  detections={result.detections}
                  peopleCount={result.people_count}
                />
              ) : (
                <div className="flex items-center justify-center h-96 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg">
                  <div className="text-center text-gray-500 dark:text-gray-400">
                    <svg
                      className="mx-auto h-12 w-12 mb-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                    <p className="text-lg">Upload an image to see detection results</p>
                    <p className="text-sm mt-2">Supported formats: JPG, PNG, WEBP</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Detection Details */}
            {result && result.detections.length > 0 && (
              <div className="mt-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-lg font-semibold mb-4 text-gray-800 dark:text-white">
                  Detection Details
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs uppercase bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                      <tr>
                        <th className="px-4 py-3">#</th>
                        <th className="px-4 py-3">Class</th>
                        <th className="px-4 py-3">Confidence</th>
                        <th className="px-4 py-3">Bounding Box</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.detections.map((detection, index) => (
                        <tr
                          key={index}
                          className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
                        >
                          <td className="px-4 py-3 font-medium">{index + 1}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
                              {detection.class_name}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center">
                              <div className="w-24 bg-gray-200 dark:bg-gray-600 rounded-full h-2 mr-2">
                                <div
                                  className="bg-green-500 h-2 rounded-full"
                                  style={{ width: `${detection.confidence * 100}%` }}
                                ></div>
                              </div>
                              <span>{(detection.confidence * 100).toFixed(1)}%</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 font-mono text-xs">
                            [{detection.bbox.map(v => v.toFixed(0)).join(', ')}]
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
