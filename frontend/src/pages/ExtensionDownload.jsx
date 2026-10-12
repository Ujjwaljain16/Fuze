import { useState, useEffect } from 'react'
import { Download, ExternalLink, CheckCircle, AlertCircle, FileArchive, Settings, Key } from 'lucide-react'

const EXTENSION_REPO = 'https://github.com/Ujjwaljain16/BookmarkExtension'
const FOLDER = 'fuze-web-clipper'

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
                            Click the button below to download the extension package (under 1 MB). Then extract it and load it in Chrome.
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
                            <li>Keep the suggested location (e.g., <code className="bg-gray-900 px-1 rounded">C:\Users\YourName\Downloads\fuze-web-clipper</code>)</li>
                            <li>Click "Extract"</li>
                            <li>You should see a <code className="bg-gray-900 px-1 rounded">{FOLDER}</code> folder containing <code className="bg-gray-900 px-1 rounded">manifest.json</code></li>
                            </>
                          )}
                          {osType === 'mac' && (
                            <>
                            <li>Locate the downloaded <code className="bg-gray-900 px-1 rounded">fuze-web-clipper.zip</code> file (usually in Downloads)</li>
                            <li>Double-click the zip file</li>
                            <li>It will automatically extract to the same location</li>
                            <li>You should see a folder named <code className="bg-gray-900 px-1 rounded">{FOLDER}</code> containing <code className="bg-gray-900 px-1 rounded">manifest.json</code></li>
                            </>
                          )}
                          {osType === 'linux' && (
                            <>
                            <li>Locate the downloaded <code className="bg-gray-900 px-1 rounded">fuze-web-clipper.zip</code> file (usually in Downloads)</li>
                            <li>Right-click on the zip file</li>
                            <li>Select "Extract Here" or "Extract to..."</li>
                            <li>You should see a folder named <code className="bg-gray-900 px-1 rounded">{FOLDER}</code> containing <code className="bg-gray-900 px-1 rounded">manifest.json</code></li>
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
                            <li>Select the extracted <code className="bg-gray-900 px-1 rounded">{FOLDER}</code> folder</li>
                            <li>The extension should now appear in your extensions list</li>
                          </ol>
                        </div>
                        
                        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
                          <div className="flex items-start gap-2">
                            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-amber-200">
                              <strong>Important:</strong> Select the folder that contains <code className="bg-gray-900 px-1 rounded">manifest.json</code> directly, not a folder above it.
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
                    <h3 className="text-xl font-semibold mb-2">Sign In</h3>
                    <p className="text-gray-400 mb-4">
                      Connect the extension to your Fuze account
                    </p>
                    
                    {downloadStep === 4 && (
                      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 space-y-4">
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <Key className="w-5 h-5 text-cyan-400" />
                            <span className="font-semibold">Two ways to sign in</span>
                          </div>
                          <ol className="list-decimal list-inside space-y-2 text-sm text-gray-300">
                            <li>Sign in on the Fuze website: the extension picks up the session by itself. If you were already signed in, reload the Fuze tab once.</li>
                            <li>Or right-click the extension icon, choose <strong>"Options"</strong>, and sign in with your Fuze email and password.</li>
                          </ol>
                          <p className="text-sm text-gray-400 mt-3">
                            In <strong>Options</strong> you can also turn on <strong>auto-sync</strong> of new Chrome bookmarks and <strong>import all</strong> your existing ones.
                          </p>
                        </div>
                        
                        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                          <div className="flex items-start gap-2">
                            <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-green-200">
                              <strong>Nothing to configure:</strong> the extension already knows Fuze's server. You only need to sign in.
                            </div>
                          </div>
                        </div>
                        
                        <button
                          onClick={() => window.location.href = '/login'}
                          className="w-full px-4 py-2 bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-600 hover:to-emerald-600 rounded-lg transition-all duration-300 flex items-center justify-center gap-2 font-semibold"
                        >
                          Sign in on Fuze
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
                        <li>Click the extension icon to save the page you are on, with its content</li>
                        <li>Right-click a page or a link and choose "Save page to Fuze" or "Save link to Fuze"</li>
                        <li>Import all your Chrome bookmarks from the extension's Options</li>
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
          <a
            href={EXTENSION_REPO}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-xl p-4 hover:border-cyan-500/30 transition-all duration-300 group"
          >
            <div className="flex items-center gap-3">
              <ExternalLink className="w-6 h-6 text-cyan-400 group-hover:scale-110 transition-transform" />
              <div>
                <h3 className="font-semibold">Manual Installation</h3>
                <p className="text-sm text-gray-400">Get the source on GitHub</p>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Clone the repository and load its folder with "Load unpacked"
            </p>
          </a>
          
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
              <p className="text-gray-400 mt-1">Select the folder that contains <code className="bg-gray-900 px-1 rounded">manifest.json</code> directly, not a folder above it.</p>
            </div>
            <div>
              <strong className="text-white">Can't connect to Fuze?</strong>
              <p className="text-gray-400 mt-1">The extension uses Fuze's server by default. If you changed <strong>API server</strong> in its Options, click <strong>"Use Fuze"</strong> there.</p>
            </div>
            <div>
              <strong className="text-white">Login not working?</strong>
              <p className="text-gray-400 mt-1">Sign in on the Fuze website and reload the tab, or sign in from the extension's Options with your Fuze email and password. After updating from an older version of the extension, sign in once again.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExtensionDownload

