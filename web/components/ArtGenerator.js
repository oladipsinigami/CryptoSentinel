const { useState, useEffect, useRef } = React;

const ArtGenerator = () => {
    // Default config values
    const defaultParams = {
        seed: 12345,
        particleCount: 5000,
        flowSpeed: 0.6,
        noiseScale: 0.006,
        trailLength: 12,
        colorPalette: ['#10b981', '#ef4444', '#8b5cf6']
    };

    // States for controls UI
    const [seed, setSeed] = useState(defaultParams.seed);
    const [particleCount, setParticleCount] = useState(defaultParams.particleCount);
    const [flowSpeed, setFlowSpeed] = useState(defaultParams.flowSpeed);
    const [noiseScale, setNoiseScale] = useState(defaultParams.noiseScale);
    const [trailLength, setTrailLength] = useState(defaultParams.trailLength);
    const [color1, setColor1] = useState(defaultParams.colorPalette[0]);
    const [color2, setColor2] = useState(defaultParams.colorPalette[1]);
    const [color3, setColor3] = useState(defaultParams.colorPalette[2]);

    // Live statistics state
    const [stats, setStats] = useState({
        winRate: "100.0%",
        netProfit: "+1.82%",
        tradesCount: "4 / 4",
        leverage: "3x Futures"
    });

    // Refs
    const p5Instance = useRef(null);
    const containerRef = useRef(null);
    const paramsRef = useRef({
        seed: defaultParams.seed,
        particleCount: defaultParams.particleCount,
        flowSpeed: defaultParams.flowSpeed,
        noiseScale: defaultParams.noiseScale,
        trailLength: defaultParams.trailLength,
        colorPalette: [...defaultParams.colorPalette]
    });

    // Keep paramsRef in sync with states
    useEffect(() => {
        paramsRef.current.seed = seed;
        paramsRef.current.particleCount = particleCount;
        paramsRef.current.flowSpeed = flowSpeed;
        paramsRef.current.noiseScale = noiseScale;
        paramsRef.current.trailLength = trailLength;
        paramsRef.current.colorPalette = [color1, color2, color3];
    }, [seed, particleCount, flowSpeed, noiseScale, trailLength, color1, color2, color3]);

    // Fetch actual live portfolio metrics to populate the stats card
    useEffect(() => {
        fetch('/api/state')
            .then(res => res.json())
            .then(data => {
                if (data.total_trades > 0) {
                    const wr = ((data.winning_trades / data.total_trades) * 100).toFixed(1) + "%";
                    const prof = (data.realized_pnl >= 0 ? "+" : "") + new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(data.realized_pnl);
                    const countStr = `${data.winning_trades} / ${data.total_trades}`;
                    
                    // extract leverage from any active position
                    let levStr = "3x Futures";
                    if (data.open_positions && data.open_positions.length > 0) {
                        levStr = `${data.open_positions[0].leverage}x Futures`;
                    }
                    
                    setStats({
                        winRate: wr,
                        netProfit: prof,
                        tradesCount: countStr,
                        leverage: levStr
                    });
                }
            })
            .catch(err => console.log("Error loading stats for art generator:", err));
    }, []);

    // Instantiate p5
    useEffect(() => {
        const sketch = (p) => {
            let particles = [];
            let flowField = [];
            let cols, rows;
            let scl = 15;

            p.setup = () => {
                // Large canvas scaled down via styles
                const canvas = p.createCanvas(1200, 1200);
                canvas.id('p5-vector-canvas');
                p.initializeSystem();
            };

            p.initializeSystem = () => {
                p.randomSeed(paramsRef.current.seed);
                p.noiseSeed(paramsRef.current.seed);

                cols = p.floor(p.width / scl);
                rows = p.floor(p.height / scl);
                flowField = new Array(cols * rows);

                particles = [];
                for (let i = 0; i < paramsRef.current.particleCount; i++) {
                    particles.push(new Particle());
                }
                
                // Dark background matching style.css --bg-main
                p.background(6, 4, 10);
            };

            p.draw = () => {
                // Apply trail effect
                let alpha = p.map(paramsRef.current.trailLength, 2, 20, 40, 4);
                p.push();
                p.fill(6, 4, 10, alpha);
                p.noStroke();
                p.rect(0, 0, p.width, p.height);
                p.pop();

                // Compute noise flow vectors
                let yoff = 0;
                for (let y = 0; y < rows; y++) {
                    let xoff = 0;
                    for (let x = 0; x < cols; x++) {
                        let index = x + y * cols;
                        let angle = p.noise(xoff, yoff, p.frameCount * 0.003) * p.TWO_PI * 4.0;
                        let v = p5.Vector.fromAngle(angle);
                        v.setMag(paramsRef.current.flowSpeed);
                        flowField[index] = v;
                        xoff += paramsRef.current.noiseScale * scl;
                    }
                    yoff += paramsRef.current.noiseScale * scl;
                }

                // Render particles
                for (let i = 0; i < particles.length; i++) {
                    particles[i].follow(flowField);
                    particles[i].update();
                    particles[i].edges();
                    particles[i].show();
                }
            };

            class Particle {
                constructor() {
                    this.pos = p.createVector(p.random(p.width), p.random(p.height));
                    this.vel = p.createVector(0, 0);
                    this.acc = p.createVector(0, 0);
                    this.maxSpeed = p.random(1.5, 4.0);
                    this.prevPos = this.pos.copy();
                    
                    let r = p.random(1.0);
                    if (r < 0.45) {
                        this.state = "long";
                        this.colorIndex = 0;
                    } else if (r < 0.85) {
                        this.state = "short";
                        this.colorIndex = 1;
                    } else {
                        this.state = "neutral";
                        this.colorIndex = 2;
                    }
                }

                update() {
                    this.vel.add(this.acc);
                    this.vel.limit(this.maxSpeed);
                    this.pos.add(this.vel);
                    this.acc.mult(0);
                }

                applyForce(force) {
                    this.acc.add(force);
                }

                follow(vectors) {
                    let x = p.floor(this.pos.x / scl);
                    let y = p.floor(this.pos.y / scl);
                    x = p.constrain(x, 0, cols - 1);
                    y = p.constrain(y, 0, rows - 1);
                    let index = x + y * cols;
                    let force = vectors[index];
                    
                    if (force) {
                        let biasedForce = force.copy();
                        
                        // Apply directional vectors based on trade perception states
                        if (this.state === "long") {
                            biasedForce.add(p.createVector(0.12, -0.25));
                        } else if (this.state === "short") {
                            biasedForce.add(p.createVector(0.12, 0.25));
                        } else {
                            biasedForce.add(p.createVector(-0.15, 0.0));
                        }
                        
                        this.applyForce(biasedForce);
                    }
                }

                edges() {
                    if (this.pos.x > p.width) {
                        this.pos.x = 0;
                        this.updatePrev();
                    }
                    if (this.pos.x < 0) {
                        this.pos.x = p.width;
                        this.updatePrev();
                    }
                    if (this.pos.y > p.height) {
                        this.pos.y = 0;
                        this.updatePrev();
                    }
                    if (this.pos.y < 0) {
                        this.pos.y = p.height;
                        this.updatePrev();
                    }
                }

                updatePrev() {
                    this.prevPos.x = this.pos.x;
                    this.prevPos.y = this.pos.y;
                }

                show() {
                    p.stroke(paramsRef.current.colorPalette[this.colorIndex]);
                    p.strokeWeight(p.random(0.7, 1.6));
                    p.line(this.pos.x, this.pos.y, this.prevPos.x, this.prevPos.y);
                    this.updatePrev();
                }
            }
        };

        p5Instance.current = new p5(sketch, containerRef.current);

        return () => {
            if (p5Instance.current) {
                p5Instance.current.remove();
            }
        };
    }, []);

    // Re-initialize system helpers
    const triggerReinit = () => {
        if (p5Instance.current) {
            p5Instance.current.initializeSystem();
        }
    };

    const handleSeedChange = (val) => {
        const num = parseInt(val) || 1;
        setSeed(num);
        setTimeout(triggerReinit, 50);
    };

    const handleRandomSeed = () => {
        const rnd = Math.floor(Math.random() * 999999) + 1;
        setSeed(rnd);
        setTimeout(triggerReinit, 50);
    };

    const handlePrevSeed = () => {
        setSeed(prev => {
            const next = Math.max(1, prev - 1);
            setTimeout(triggerReinit, 50);
            return next;
        });
    };

    const handleNextSeed = () => {
        setSeed(prev => {
            const next = prev + 1;
            setTimeout(triggerReinit, 50);
            return next;
        });
    };

    const handleParamChange = (setter, val, isResetRequiring = false) => {
        setter(val);
        if (isResetRequiring) {
            setTimeout(triggerReinit, 50);
        }
    };

    const handleReset = () => {
        setSeed(defaultParams.seed);
        setParticleCount(defaultParams.particleCount);
        setFlowSpeed(defaultParams.flowSpeed);
        setNoiseScale(defaultParams.noiseScale);
        setTrailLength(defaultParams.trailLength);
        setColor1(defaultParams.colorPalette[0]);
        setColor2(defaultParams.colorPalette[1]);
        setColor3(defaultParams.colorPalette[2]);
        setTimeout(triggerReinit, 80);
    };

    const handleDownload = () => {
        if (p5Instance.current) {
            p5Instance.current.saveCanvas('stochastic_ascendance_' + seed, 'png');
        }
    };

    return (
        <div className="relative w-full min-h-screen bg-black text-white pt-24 pb-12 px-4 md:px-8 lg:px-16 z-10 flex flex-col justify-between overflow-x-hidden">
            {/* Background looping FadingVideo */}
            <window.FadingVideo 
                src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_094631_d30ab262-45ee-4b7d-99f3-5d5848c8ef13.mp4"
                className="absolute inset-0 w-full h-full object-cover z-0 opacity-10 pointer-events-none"
            />

            <div className="relative z-10 max-w-[1400px] w-full mx-auto grid grid-cols-1 lg:grid-cols-4 gap-6">
                
                {/* Controls Sidebar */}
                <div className="lg:col-span-1 flex flex-col gap-5 liquid-glass rounded-2xl p-6 shadow-xl h-fit border border-white/5 font-body text-xs">
                    
                    {/* Panel 1: Stats */}
                    <div className="border-b border-white/10 pb-4">
                        <h3 className="font-heading italic text-xl text-white mb-3 uppercase tracking-wider">Sentinel Stats</h3>
                        <div className="grid grid-cols-2 gap-2 bg-black/35 p-3 rounded-xl border border-white/5">
                            <div>
                                <span className="text-[10px] text-white/40 block">Win Rate</span>
                                <span className="text-sm font-semibold text-emerald-400 block">{stats.winRate}</span>
                            </div>
                            <div>
                                <span className="text-[10px] text-white/40 block">Net Profit</span>
                                <span className="text-sm font-semibold text-emerald-400 block">{stats.netProfit}</span>
                            </div>
                            <div className="mt-1">
                                <span className="text-[10px] text-white/40 block">Trades</span>
                                <span className="text-sm font-semibold text-white/80 block">{stats.tradesCount}</span>
                            </div>
                            <div className="mt-1">
                                <span className="text-[10px] text-white/40 block">Leverage</span>
                                <span className="text-sm font-semibold text-white/80 block">{stats.leverage}</span>
                            </div>
                        </div>
                    </div>

                    {/* Panel 2: Seeds */}
                    <div className="border-b border-white/10 pb-4 flex flex-col gap-2.5">
                        <h3 className="font-heading italic text-xl text-white uppercase tracking-wider">Seed Control</h3>
                        <input 
                            type="number"
                            value={seed}
                            onChange={(e) => handleSeedChange(e.target.value)}
                            className="w-full bg-black/40 border border-white/10 rounded-lg p-2 font-mono text-center text-sm text-white"
                        />
                        <div className="grid grid-cols-2 gap-2">
                            <button 
                                onClick={handlePrevSeed}
                                className="p-2 bg-white/5 border border-white/10 hover:bg-white/10 rounded-lg font-semibold flex items-center justify-center gap-1 transition-all"
                            >
                                <i className="fa-solid fa-arrow-left"></i> Prev
                            </button>
                            <button 
                                onClick={handleNextSeed}
                                className="p-2 bg-white/5 border border-white/10 hover:bg-white/10 rounded-lg font-semibold flex items-center justify-center gap-1 transition-all"
                            >
                                Next <i class="fa-solid fa-arrow-right"></i>
                            </button>
                        </div>
                        <button 
                            onClick={handleRandomSeed}
                            className="w-full py-2 bg-white/5 border border-white/10 hover:bg-white/10 rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-all"
                        >
                            <i className="fa-solid fa-shuffle"></i> Random Seed
                        </button>
                    </div>

                    {/* Panel 3: Flow Parameters */}
                    <div className="border-b border-white/10 pb-4 flex flex-col gap-4">
                        <h3 className="font-heading italic text-xl text-white uppercase tracking-wider">Flow Parameters</h3>
                        
                        {/* Particles */}
                        <div className="flex flex-col gap-1">
                            <div className="flex justify-between items-center text-[10px] text-white/60">
                                <span>Particles Count</span>
                                <span className="font-mono text-white">{particleCount}</span>
                            </div>
                            <input 
                                type="range" 
                                min="1000" 
                                max="10000" 
                                step="500"
                                value={particleCount}
                                onChange={(e) => handleParamChange(setParticleCount, parseInt(e.target.value), true)}
                                className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-violet-400"
                            />
                        </div>

                        {/* Flow Speed */}
                        <div className="flex flex-col gap-1">
                            <div className="flex justify-between items-center text-[10px] text-white/60">
                                <span>Flow Speed</span>
                                <span className="font-mono text-white">{flowSpeed.toFixed(1)}</span>
                            </div>
                            <input 
                                type="range" 
                                min="0.1" 
                                max="2.0" 
                                step="0.1"
                                value={flowSpeed}
                                onChange={(e) => handleParamChange(setFlowSpeed, parseFloat(e.target.value), false)}
                                className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-violet-400"
                            />
                        </div>

                        {/* Volatility */}
                        <div className="flex flex-col gap-1">
                            <div className="flex justify-between items-center text-[10px] text-white/60">
                                <span>Volatility Scale</span>
                                <span className="font-mono text-white">{noiseScale.toFixed(3)}</span>
                            </div>
                            <input 
                                type="range" 
                                min="0.001" 
                                max="0.02" 
                                step="0.001"
                                value={noiseScale}
                                onChange={(e) => handleParamChange(setNoiseScale, parseFloat(e.target.value), false)}
                                className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-violet-400"
                            />
                        </div>

                        {/* Trail persistence */}
                        <div className="flex flex-col gap-1">
                            <div className="flex justify-between items-center text-[10px] text-white/60">
                                <span>Trail Persistence</span>
                                <span className="font-mono text-white">{trailLength}</span>
                            </div>
                            <input 
                                type="range" 
                                min="2" 
                                max="20" 
                                step="1"
                                value={trailLength}
                                onChange={(e) => handleParamChange(setTrailLength, parseInt(e.target.value), false)}
                                className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-violet-400"
                            />
                        </div>
                    </div>

                    {/* Panel 4: Colors */}
                    <div className="border-b border-white/10 pb-4 flex flex-col gap-2">
                        <h3 className="font-heading italic text-xl text-white uppercase tracking-wider">Signal Palette</h3>
                        
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] text-white/60">BUY / LONG Vector</span>
                            <div className="flex items-center gap-1.5 font-mono">
                                <input type="color" value={color1} onChange={(e) => setColor1(e.target.value)} className="w-6 h-6 border-0 bg-transparent cursor-pointer rounded" />
                                <span className="text-[10px] text-white/40">{color1}</span>
                            </div>
                        </div>

                        <div className="flex items-center justify-between">
                            <span className="text-[10px] text-white/60">SELL / SHORT Vector</span>
                            <div className="flex items-center gap-1.5 font-mono">
                                <input type="color" value={color2} onChange={(e) => setColor2(e.target.value)} className="w-6 h-6 border-0 bg-transparent cursor-pointer rounded" />
                                <span className="text-[10px] text-white/40">{color2}</span>
                            </div>
                        </div>

                        <div className="flex items-center justify-between">
                            <span className="text-[10px] text-white/60">HOLD / Neutral Vector</span>
                            <div className="flex items-center gap-1.5 font-mono">
                                <input type="color" value={color3} onChange={(e) => setColor3(e.target.value)} className="w-6 h-6 border-0 bg-transparent cursor-pointer rounded" />
                                <span className="text-[10px] text-white/40">{color3}</span>
                            </div>
                        </div>
                    </div>

                    {/* Panel 5: Actions */}
                    <div className="flex flex-col gap-2">
                        <button 
                            onClick={handleReset}
                            className="w-full py-2 bg-white/5 border border-white/10 hover:bg-white/10 rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-all"
                        >
                            <i className="fa-solid fa-undo"></i> Reset Defaults
                        </button>
                        <button 
                            onClick={handleDownload}
                            className="w-full py-2 bg-emerald-500 hover:bg-emerald-600 text-black rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-all"
                        >
                            <i className="fa-solid fa-download"></i> Download PNG
                        </button>
                    </div>

                </div>

                {/* Canvas Container */}
                <div className="lg:col-span-3 flex items-center justify-center min-w-0">
                    <div className="w-full max-w-[800px] rounded-2xl overflow-hidden border border-white/15 shadow-2xl relative aspect-square bg-[#020104]" ref={containerRef}>
                        {/* Canvas mounts here */}
                    </div>
                </div>

            </div>

            {/* Footer */}
            <div className="text-center text-[11px] text-white/30 mt-6 pt-4 border-t border-white/10 font-body">
                &copy; 2026 CryptoSentinel AI Trading Framework. Built for the Bitget AI Base Camp Hackathon.
            </div>
        </div>
    );
};

window.ArtGenerator = ArtGenerator;
