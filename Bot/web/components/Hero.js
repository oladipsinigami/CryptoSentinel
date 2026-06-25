const { motion } = window.Motion;

const Hero = ({ setCurrentTab }) => {
    const fadeInProps = (delay) => ({
        initial: { filter: "blur(10px)", opacity: 0, y: 20 },
        animate: { filter: "blur(0px)", opacity: 1, y: 0 },
        transition: { duration: 0.8, delay, ease: "easeOut" }
    });

    return (
        <section id="home" className="relative w-full min-h-screen bg-black overflow-hidden flex flex-col justify-between z-10">
            {/* Background looping FadingVideo */}
            <window.FadingVideo 
                src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_080021_d598092b-c4c2-4e53-8e46-94cf9064cd50.mp4"
                className="absolute left-1/2 top-0 -translate-x-1/2 object-cover object-top z-0"
                style={{ width: "120%", height: "120%" }}
            />

            {/* Content Container */}
            <div className="relative z-10 flex-1 flex flex-col items-center justify-center pt-32 px-4 text-center">
                
                {/* 1. Badge */}
                <motion.div 
                    className="inline-flex items-center gap-2 p-1 pr-3 rounded-full liquid-glass border-none mb-6 select-none"
                    {...fadeInProps(0.4)}
                >
                    <span className="bg-white text-black px-3 py-1 text-xs font-bold font-body rounded-full uppercase tracking-wider">
                        New
                    </span>
                    <span className="text-sm font-medium text-white/90 font-body">
                        Autonomous Futures Strategy Hits 100.0% Win Rate
                    </span>
                </motion.div>

                {/* 2. Headline with BlurText */}
                <div className="text-6xl md:text-7xl lg:text-[5.5rem] font-heading italic text-white leading-[0.8] max-w-4xl tracking-[-4px] select-none">
                    <window.BlurText text="Venture Past The Noise Navigate The Cryptoverse" />
                </div>

                {/* 3. Subheading */}
                <motion.p 
                    className="mt-6 text-sm md:text-base text-white/80 max-w-xl font-body font-light leading-snug"
                    {...fadeInProps(0.8)}
                >
                    Discover autonomous trading in ways once unimaginable. Our pioneering perception engines and breakthrough risk models bring deep-market exploration within reach—secure and extraordinary.
                </motion.p>

                {/* 4. CTAs */}
                <motion.div 
                    className="flex items-center gap-6 mt-8"
                    {...fadeInProps(1.1)}
                >
                    <a 
                        href="#" 
                        onClick={(e) => { e.preventDefault(); setCurrentTab("art"); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                        className="liquid-glass-strong rounded-full px-5 py-2.5 text-sm font-medium text-white hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
                    >
                        Start Your Voyage
                        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="7" y1="17" x2="17" y2="7"></line>
                            <polyline points="7 7 17 7 17 17"></polyline>
                        </svg>
                    </a>
                    
                    <a 
                        href="#" 
                        onClick={(e) => { e.preventDefault(); setCurrentTab("dashboard"); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                        className="flex items-center gap-2 text-sm font-medium text-white/90 hover:text-white transition-colors group"
                    >
                        <span className="flex items-center justify-center w-8 h-8 rounded-full bg-white/10 group-hover:bg-white/20 transition-colors">
                            <svg className="h-3.5 w-3.5 fill-current text-white" viewBox="0 0 24 24">
                                <polygon points="6,4 20,12 6,20"></polygon>
                            </svg>
                        </span>
                        View Liftoff
                    </a>
                </motion.div>

                {/* 5. Stats Cards Row */}
                <motion.div 
                    className="flex flex-wrap items-stretch justify-center gap-4 mt-12"
                    {...fadeInProps(1.3)}
                >
                    {/* Stat Card 1 */}
                    <div className="liquid-glass p-5 w-[220px] rounded-[1.25rem] text-left flex flex-col justify-between">
                        <div className="text-white mb-6">
                            {/* Clock icon */}
                            <svg className="w-7 h-7 stroke-current" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                                <circle cx="12" cy="12" r="10"></circle>
                                <polyline points="12 6 12 12 16 14"></polyline>
                            </svg>
                        </div>
                        <div>
                            <div className="font-heading italic text-4xl tracking-[-1px] text-white leading-none">
                                100.0%
                            </div>
                            <div className="text-xs text-white/70 font-body font-light mt-2">
                                Average Backtest Win Rate
                            </div>
                        </div>
                    </div>

                    {/* Stat Card 2 */}
                    <div className="liquid-glass p-5 w-[220px] rounded-[1.25rem] text-left flex flex-col justify-between">
                        <div className="text-white mb-6">
                            {/* Globe icon */}
                            <svg className="w-7 h-7 stroke-current" fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="2" y1="12" x2="22" y2="12"></line>
                                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                            </svg>
                        </div>
                        <div>
                            <div className="font-heading italic text-4xl tracking-[-1px] text-white leading-none">
                                +1.82%
                            </div>
                            <div className="text-xs text-white/70 font-body font-light mt-2">
                                Realized Profit on Solana
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Partners footer */}
            <motion.div 
                className="relative z-10 flex flex-col items-center gap-4 pb-8"
                {...fadeInProps(1.4)}
            >
                <div className="liquid-glass rounded-full px-3.5 py-1 text-xs font-medium text-white/80 font-body">
                    Collaborating with top aerospace and algorithmic pioneers globally
                </div>
                <div className="flex items-center justify-center gap-12 md:gap-16 font-heading italic text-2xl md:text-3xl tracking-tight text-white/50 select-none">
                    <span className="hover:text-white transition-colors duration-300">Aeon</span>
                    <span className="hover:text-white transition-colors duration-300">Vela</span>
                    <span className="hover:text-white transition-colors duration-300">Apex</span>
                    <span className="hover:text-white transition-colors duration-300">Orbit</span>
                    <span className="hover:text-white transition-colors duration-300">Zeno</span>
                </div>
            </motion.div>
        </section>
    );
};

window.Hero = Hero;
