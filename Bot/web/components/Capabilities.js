const { motion } = window.Motion;

const Capabilities = () => {
    const cardAnimation = (delay) => ({
        initial: { opacity: 0, y: 30, filter: "blur(5px)" },
        whileInView: { opacity: 1, y: 0, filter: "blur(0px)" },
        viewport: { once: true, margin: "-100px" },
        transition: { duration: 0.8, delay, ease: "easeOut" }
    });

    return (
        <section id="innovation" className="relative w-full min-h-screen bg-black overflow-hidden flex flex-col justify-between z-10">
            {/* Background looping FadingVideo */}
            <window.FadingVideo 
                src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_094631_d30ab262-45ee-4b7d-99f3-5d5848c8ef13.mp4"
                className="absolute inset-0 w-full h-full object-cover z-0"
            />

            {/* Content Container */}
            <div className="relative z-10 px-8 md:px-16 lg:px-20 pt-24 pb-12 flex flex-col min-h-screen justify-between">
                
                {/* Header (Top of Section) */}
                <div className="mb-auto">
                    <motion.div 
                        className="text-sm font-body text-white/80 uppercase tracking-widest mb-6"
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.6 }}
                    >
                        // Capabilities
                    </motion.div>
                    
                    <motion.h2 
                        className="font-heading italic text-white text-6xl md:text-7xl lg:text-[6rem] leading-[0.9] tracking-[-3px] select-none"
                        initial={{ opacity: 0, y: 30 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                    >
                        Trading<br />evolved
                    </motion.h2>
                </div>

                {/* Capabilities Grid (Bottom of Section) */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
                    
                    {/* Card 1: AI Perception */}
                    <motion.div 
                        className="liquid-glass rounded-[1.25rem] p-6 min-h-[360px] flex flex-col justify-between hover:bg-white/[0.03] transition-all"
                        {...cardAnimation(0.2)}
                    >
                        {/* Top row */}
                        <div className="flex items-start justify-between gap-4">
                            {/* Icon container */}
                            <div className="w-11 h-11 rounded-[0.75rem] liquid-glass flex items-center justify-center text-white">
                                <svg className="h-6 w-6 fill-current" viewBox="0 0 24 24">
                                    <path d="M5 21q-.825 0-1.412-.587T3 19V5q0-.825.588-1.412T5 3h14q.825 0 1.413.588T21 5v14q0 .825-.587 1.413T19 21H5Zm1-4h12l-3.75-5-3 4L9 13l-3 4Z" />
                                </svg>
                            </div>
                            {/* Tags */}
                            <div className="flex flex-wrap justify-end gap-1.5 max-w-[70%]">
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Real-Time Feed
                                </span>
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Multi-Source
                                </span>
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    News Sentiment
                                </span>
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Volatility Scan
                                </span>
                            </div>
                        </div>

                        {/* Bottom Info */}
                        <div className="mt-8">
                            <h3 className="font-heading italic text-white text-3xl md:text-4xl tracking-[-1px] leading-none select-none">
                                AI Perception
                            </h3>
                            <p className="mt-3 text-sm text-white/90 font-body font-light leading-snug max-w-[32ch]">
                                AI analyzes social sentiment and macroeconomic trends to scan for volatility and construct trade perceptions.
                            </p>
                        </div>
                    </motion.div>

                    {/* Card 2: Autonomous Execution */}
                    <motion.div 
                        className="liquid-glass rounded-[1.25rem] p-6 min-h-[360px] flex flex-col justify-between hover:bg-white/[0.03] transition-all"
                        {...cardAnimation(0.4)}
                    >
                        {/* Top row */}
                        <div className="flex items-start justify-between gap-4">
                            {/* Icon container */}
                            <div className="w-11 h-11 rounded-[0.75rem] liquid-glass flex items-center justify-center text-white">
                                <svg className="h-6 w-6 fill-current" viewBox="0 0 24 24">
                                    <path d="M4 6.47 5.76 10H20v8H4V6.47M22 4h-4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.89-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4Z" />
                                </svg>
                            </div>
                            {/* Tags */}
                            <div className="flex flex-wrap justify-end gap-1.5 max-w-[70%]">
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Scale Fast
                                </span>
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Multi-Leverage
                                </span>
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Smart Reversals
                                </span>
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Instant Execution
                                </span>
                            </div>
                        </div>

                        {/* Bottom Info */}
                        <div className="mt-8">
                            <h3 className="font-heading italic text-white text-3xl md:text-4xl tracking-[-1px] leading-none select-none">
                                Autonomous Execution
                            </h3>
                            <p className="mt-3 text-sm text-white/90 font-body font-light leading-snug max-w-[32ch]">
                                Scale and reverse positions automatically. Create a unified trading flow for Solana and Bitcoin without manual delays.
                            </p>
                        </div>
                    </motion.div>

                    {/* Card 3: Risk Management */}
                    <motion.div 
                        className="liquid-glass rounded-[1.25rem] p-6 min-h-[360px] flex flex-col justify-between hover:bg-white/[0.03] transition-all"
                        {...cardAnimation(0.6)}
                    >
                        {/* Top row */}
                        <div className="flex items-start justify-between gap-4">
                            {/* Icon container */}
                            <div className="w-11 h-11 rounded-[0.75rem] liquid-glass flex items-center justify-center text-white">
                                <svg className="h-6 w-6 fill-current" viewBox="0 0 24 24">
                                    <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1Zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7Z" />
                                </svg>
                            </div>
                            {/* Tags */}
                            <div className="flex flex-wrap justify-end gap-1.5 max-w-[70%]">
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    ATR Stop-Loss
                                </span>
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Take-Profit
                                </span>
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Liquidation Shield
                                </span>
                                <span className="liquid-glass rounded-full px-3 py-1 text-[11px] text-white/90 font-body whitespace-nowrap">
                                    Safety Halts
                                </span>
                            </div>
                        </div>

                        {/* Bottom Info */}
                        <div className="mt-8">
                            <h3 className="font-heading italic text-white text-3xl md:text-4xl tracking-[-1px] leading-none select-none">
                                Risk Management
                            </h3>
                            <p className="mt-3 text-sm text-white/90 font-body font-light leading-snug max-w-[32ch]">
                                Dynamic leverage and risk adjustment. Shield your capital with volatility-weighted stop-losses and automation limits.
                            </p>
                        </div>
                    </motion.div>
                </div>
            </div>
        </section>
    );
};

window.Capabilities = Capabilities;
