import React, { useState } from 'react';
import axios from 'axios';
import { LayoutDashboard, CheckCircle2, AlertCircle } from 'lucide-react';

const API_URL = 'http://localhost:3001/api/otp';

function App() {
  const [userOtp, setUserOtp] = useState('');
  const [verifyStatus, setVerifyStatus] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);

  const handleVerify = async (e) => {
    e.preventDefault();
    setVerifyStatus(null);
    setIsVerifying(true);
    
    try {
      const res = await axios.post(`${API_URL}/verify`, { otp: userOtp });
      setVerifyStatus({
        success: res.data.valid,
        message: res.data.message
      });
      if (res.data.valid) setUserOtp('');
    } catch (err) {
      setVerifyStatus({
        success: false,
        message: err.response?.data?.message || 'Server connection failed.'
      });
    }
    setIsVerifying(false);
  };

  return (
    <div className="min-h-screen p-8 flex items-center justify-center">
      <div className="max-w-md w-full">
        
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white mb-2">Login Portal</h1>
          <p className="text-[#8b949e]">Enter your OTP to verify your identity.</p>
        </div>

        {/* CLIENT SIDE */}
        <div className="box client-box rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center gap-3 mb-6">
            <LayoutDashboard className="w-6 h-6 text-[#238636]" />
            <h2 className="text-xl font-bold text-[#238636]">Client Identity Check</h2>
          </div>
          
          <form onSubmit={handleVerify} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-[#8b949e] mb-2">
                Enter 6-digit OTP (from Visualizer):
              </label>
              <input
                type="text"
                maxLength={6}
                value={userOtp}
                onChange={(e) => setUserOtp(e.target.value.replace(/\D/g, ''))}
                placeholder="e.g. 123456"
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3 text-xl font-mono text-white focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#58a6ff] transition-colors tracking-widest text-center"
              />
            </div>
            
            <button 
              type="submit"
              disabled={userOtp.length !== 6 || isVerifying}
              className="w-full bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {isVerifying ? 'Verifying...' : 'Verify OTP'}
            </button>
          </form>

          {/* Status Message */}
          {verifyStatus && (
            <div className={`mt-6 p-4 rounded-lg flex items-start gap-3 border ${
              verifyStatus.success 
                ? 'bg-[#238636]/10 border-[#238636] text-[#3fb950]' 
                : 'bg-[#da3633]/10 border-[#da3633] text-[#ff7b72]'
            }`}>
              {verifyStatus.success ? (
                <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              )}
              <span className="font-medium text-sm">{verifyStatus.message}</span>
            </div>
          )}
        </div>
        
        <div className="text-center mt-6">
            <a href="http://localhost:3001" target="_blank" rel="noreferrer" className="text-[#58a6ff] hover:underline text-sm">
                Open Server Generator Visualizer ↗
            </a>
        </div>

      </div>
    </div>
  );
}

export default App;
