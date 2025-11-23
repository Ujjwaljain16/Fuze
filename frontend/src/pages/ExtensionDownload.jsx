import { useState, useEffect } from 'react'
import { Download, ExternalLink, CheckCircle, AlertCircle, FileArchive, Settings, Key } from 'lucide-react'

const ExtensionDownload = () => {
  const [downloadStep, setDownloadStep] = useState(1)
  const [osType, setOsType] = useState('windows')

  useEffect(() => {
    // Detect OS
    const userAgent = navigator.userAgent.toLowerCase()
    if (userAgent.includes('win')) {
      setOsType('windows')
    } else if (userAgent.includes('mac')) {
      setOsType('mac')
    } else {
      setOsType('linux')
    }
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 text-white p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-cyan-500 to-emerald-500 rounded-2xl mb-4">
            <Download className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
            Install Fuze Web Clipper
          </h1>
          <p className="text-gray-400 text-lg">
            One-click bookmarking from any webpage
          </p>
        </div>

        {/* Installation Steps */}
        <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 md:p-8 mb-6">
          <div className="space-y-6">
            {/* Step 1: Download */}
            {downloadStep >= 1 && (
              <div className={`transition-all duration-300 ${downloadStep === 1 ? 'opacity-100' : 'opacity-60'}`}>
                <div className="flex items-start gap-4">
                  <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
                    downloadStep > 1 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-cyan-500/20 text-cyan-400'
                  }`}>
                    {downloadStep > 1 ? <CheckCircle className="w-6 h-6" /> : '1'}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold mb-2">Download Extension</h3>
                    <p className="text-gray-400 mb-4">
                      Download the Fuze Web Clipper extension package
                    </p>
                    
                    {downloadStep === 1 && (
                      <div className="space-y-4">
                        <div className="bg-gradient-to-r from-cyan-500/20 to-emerald-500/20 border border-cyan-500/30 rounded-lg p-4">
                          <p className="text-sm text-white mb-3 font-semibold">
                            📦 Download Fuze Web Clipper Extension
                          </p>
                          <p className="text-sm text-gray-300 mb-4">
                            Click the button below to download the extension package (~2.4 MB). Then extract it and load it in Chrome.
                          </p>
                          
                          <a
                            href="/extension/fuze-web-clipper.zip"
                            download="fuze-web-clipper.zip"
                            onClick={() => {
                              // Move to next step after a short delay to allow download to start
                              setTimeout(() => setDownloadStep(2), 500)
                            }}
                            className="w-full px-6 py-3 bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-600 hover:to-emerald-600 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 flex items-center justify-center gap-2"
                          >
                            <Download className="w-5 h-5" />
                            Download Fuze Web Clipper (ZIP)
                          </a>
                          
                          <p className="text-xs text-gray-400 mt-2 text-center">
                            ⚡ Quick download • No GitHub required • Ready to install
                          </p>
                        </div>
                        
                        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                          <p className="text-xs text-blue-200">
                            <strong>💡 What's next?</strong> After the download completes, click "I've downloaded the file" below to continue with extraction and installation steps.
                          </p>
                        </div>
                        
                        <button
                          onClick={() => setDownloadStep(2)}
                          className="w-full px-4 py-2 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded-lg transition-all duration-300 text-sm"
                        >
                          I've downloaded the file →
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Extract */}
            {downloadStep >= 2 && (
              <div className={`transition-all duration-300 ${downloadStep === 2 ? 'opacity-100' : 'opacity-60'}`}>
                <div className="flex items-start gap-4">
                  <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
                    downloadStep > 2 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-cyan-500/20 text-cyan-400'
                  }`}>
                    {downloadStep > 2 ? <CheckCircle className="w-6 h-6" /> : '2'}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold mb-2">Extract Extension</h3>
                    <p className="text-gray-400 mb-4">
                      Extract the downloaded zip file to a folder
                    </p>
                    
                    {downloadStep === 2 && (
                      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                        <div className="flex items-center gap-2 mb-2">
                          <FileArchive className="w-5 h-5 text-cyan-400" />
                          <span className="font-semibold">Extraction Instructions</span>
                        </div>
                        <ol className="list-decimal list-inside space-y-2 text-sm text-gray-300">
                          {osType === 'windows' && (
                            <>
                            <li>Locate the downloaded <code className="bg-gray-900 px-1 rounded">fuze-web-clipper.zip</code> file (usually in Downloads)</li>
                            <li>Right-click on the zip file</li>
                            <li>Select "Extract All..." or "Extract to..."</li>
                            <li>Choose a location (e.g., <code className="bg-gray-900 px-1 rounded">C:\Users\YourName\Downloads\fuze-web-clipper</code>)</li>
                            <li>Click "Extract"</li>
                            <li>You should see a <code className="bg-gray-900 px-1 rounded">BookmarkExtension</code> folder after extraction</li>
                            </>
                          )}
                          {osType === 'mac' && (
                            <>
                            <li>Locate the downloaded <code className="bg-gray-900 px-1 rounded">fuze-web-clipper.zip</code> file (usually in Downloads)</li>
                            <li>Double-click the zip file</li>
                            <li>It will automatically extract to the same location</li>
                            <li>You should see a folder named <code className="bg-gray-900 px-1 rounded">BookmarkExtension</code></li>
                            </>
                          )}
                          {osType === 'linux' && (
                            <>
                            <li>Locate the downloaded <code className="bg-gray-900 px-1 rounded">fuze-web-clipper.zip</code> file (usually in Downloads)</li>
                            <li>Right-click on the zip file</li>
                            <li>Select "Extract Here" or "Extract to..."</li>
                            <li>You should see a folder named <code className="bg-gray-900 px-1 rounded">BookmarkExtension</code></li>
                            </>
                          )}
                        </ol>
                        <button
                          onClick={() => setDownloadStep(3)}
                          className="mt-4 px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 rounded-lg transition-all duration-300 text-sm"
                        >
                          I've extracted the folder
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Install */}
            {downloadStep >= 3 && (
              <div className={`transition-all duration-300 ${downloadStep === 3 ? 'opacity-100' : 'opacity-60'}`}>
                <div className="flex items-start gap-4">
                  <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
                    downloadStep > 3 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-cyan-500/20 text-cyan-400'
                  }`}>
                    {downloadStep > 3 ? <CheckCircle className="w-6 h-6" /> : '3'}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold mb-2">Load Extension in Chrome</h3>
                    <p className="text-gray-400 mb-4">
                      Install the extension in Chrome using Developer Mode
                    </p>
                    
                    {downloadStep === 3 && (
                      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 space-y-4">
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <Settings className="w-5 h-5 text-cyan-400" />
                            <span className="font-semibold">Step-by-Step Instructions</span>
                          </div>
                          <ol className="list-decimal list-inside space-y-2 text-sm text-gray-300">
                            <li>Open Chrome and navigate to <code className="bg-gray-900 px-1 rounded">chrome://extensions/</code></li>
                            <li>Enable <strong>"Developer mode"</strong> toggle in the top-right corner</li>
                            <li>Click <strong>"Load unpacked"</strong> button</li>
                            <li>Navigate to and select the extracted <code className="bg-gray-900 px-1 rounded">BookmarkExtension</code> folder</li>
                            <li>The extension should now appear in your extensions list</li>
                          </ol>
                        </div>
                        
                        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
                          <div className="flex items-start gap-2">
                            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-amber-200">
                              <strong>Important:</strong> Make sure you select the <code className="bg-gray-900 px-1 rounded">BookmarkExtension</code> folder itself, not a parent folder. The folder should contain <code className="bg-gray-900 px-1 rounded">MANIFEST.JSON</code> directly.
                            </div>
                          </div>
                        </div>
                        
                        <button
                          onClick={() => window.open('chrome://extensions/', '_blank')}
                          className="w-full px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 rounded-lg transition-all duration-300 flex items-center justify-center gap-2"
                        >
                          <ExternalLink className="w-4 h-4" />
                          Open Chrome Extensions Page
                        </button>
                        
                        <button
                          onClick={() => setDownloadStep(4)}
                          className="w-full px-4 py-2 bg-green-500/20 hover:bg-green-500/30 border border-green-500/50 rounded-lg transition-all duration-300 text-sm"
                        >
                          I've installed the extension
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 4: Configure */}
            {downloadStep >= 4 && (
              <div className={`transition-all duration-300 ${downloadStep === 4 ? 'opacity-100' : 'opacity-60'}`}>
                <div className="flex items-start gap-4">
                  <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
                    downloadStep > 4 
                      ? 'bg-green-500/20 text-green-400' 
                      : 'bg-cyan-500/20 text-cyan-400'
                  }`}>
                    {downloadStep > 4 ? <CheckCircle className="w-6 h-6" /> : '4'}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold mb-2">Configure Extension</h3>
                    <p className="text-gray-400 mb-4">
                      Set up the extension with your Fuze account
                    </p>
                    
                    {downloadStep === 4 && (
                      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 space-y-4">
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <Key className="w-5 h-5 text-cyan-400" />
                            <span className="font-semibold">Configuration Steps</span>
                          </div>
                          <ol className="list-decimal list-inside space-y-2 text-sm text-gray-300">
                            <li>Click the Fuze Web Clipper icon in your Chrome toolbar</li>
                            <li>Click <strong>"Settings"</strong> in the popup</li>
                            <li>Enter your Fuze API URL: <code className="bg-gray-900 px-1 rounded">https://Ujjwaljain16-fuze-backend.hf.space</code></li>
                            <li>Enter your Fuze email and password</li>
                            <li>Click <strong>"Login to Fuze"</strong></li>
                            <li>Enable <strong>"Auto-sync Chrome bookmarks"</strong> if desired</li>
                            <li>Click <strong>"Save Settings"</strong></li>
                          </ol>
                        </div>
                        
                        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                          <div className="flex items-start gap-2">
                            <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-green-200">
                              <strong>Default Settings:</strong> The extension is pre-configured with production URLs. You only need to log in with your Fuze credentials.
                            </div>
                          </div>
                        </div>
                        
                        <button
                          onClick={() => window.location.href = '/login'}
                          className="w-full px-4 py-2 bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-600 hover:to-emerald-600 rounded-lg transition-all duration-300 flex items-center justify-center gap-2 font-semibold"
                        >
                          Go to Login
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 5: Done */}
            {downloadStep >= 5 && (
              <div className="transition-all duration-300">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg bg-green-500/20 text-green-400">
                    <CheckCircle className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold mb-2">You're All Set!</h3>
                    <p className="text-gray-400 mb-4">
                      The Fuze Web Clipper is now installed and ready to use
                    </p>
                    
                    <div className="bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-500/30 rounded-lg p-4">
                      <h4 className="font-semibold mb-2 text-green-300">How to Use:</h4>
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-300">
                        <li>Click the extension icon to save the current page</li>
                        <li>Right-click any link and select "Save to Fuze"</li>
                        <li>Use "Import All Bookmarks" to sync your Chrome bookmarks</li>
                      </ul>
                    </div>
                    
                    <div className="mt-4 flex gap-3">
                      <button
                        onClick={() => window.location.href = '/dashboard'}
                        className="flex-1 px-4 py-2 bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-600 hover:to-emerald-600 rounded-lg transition-all duration-300 font-semibold"
                      >
                        Go to Dashboard
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quick Links */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-xl p-4 hover:border-cyan-500/30 transition-all duration-300 group">
            <div className="flex items-center gap-3">
              <ExternalLink className="w-6 h-6 text-cyan-400 group-hover:scale-110 transition-transform" />
              <div>
                <h3 className="font-semibold">Manual Installation</h3>
                <p className="text-sm text-gray-400">Download from repository</p>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Clone the repository and navigate to the <code className="bg-gray-900 px-1 rounded">BookmarkExtension</code> folder
            </p>
          </div>
          
          <a
            href="/dashboard"
            className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-xl p-4 hover:border-emerald-500/30 transition-all duration-300 group"
          >
            <div className="flex items-center gap-3">
              <CheckCircle className="w-6 h-6 text-emerald-400 group-hover:scale-110 transition-transform" />
              <div>
                <h3 className="font-semibold">Back to Dashboard</h3>
                <p className="text-sm text-gray-400">Start using Fuze</p>
              </div>
            </div>
          </a>
        </div>

        {/* Troubleshooting */}
        <div className="mt-6 bg-gray-800/30 border border-gray-700 rounded-xl p-6">
          <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <AlertCircle className="w-6 h-6 text-amber-400" />
            Troubleshooting
          </h3>
          <div className="space-y-3 text-sm text-gray-300">
            <div>
              <strong className="text-white">Extension not loading?</strong>
              <p className="text-gray-400 mt-1">Make sure you selected the correct folder (should contain MANIFEST.JSON directly)</p>
            </div>
            <div>
              <strong className="text-white">Can't connect to Fuze?</strong>
              <p className="text-gray-400 mt-1">Verify the API URL is set to: <code className="bg-gray-900 px-1 rounded">https://Ujjwaljain16-fuze-backend.hf.space</code></p>
            </div>
            <div>
              <strong className="text-white">Login not working?</strong>
              <p className="text-gray-400 mt-1">Make sure you're using the same credentials as your Fuze web account</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExtensionDownload

