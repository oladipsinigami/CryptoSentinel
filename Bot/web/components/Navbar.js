const { motion } = window.Motion;

const Navbar = ({ currentTab, setCurrentTab }) => {
    const handleTabChange = (tabName, e) => {
        if (e) e.preventDefault();
        setCurrentTab(tabName);
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    const handleScrollToSection = (sectionId, e) => {
        if (e) e.preventDefault();
        if (currentTab !== "home") {
            setCurrentTab("home");
            setTimeout(() => {
                const el = document.getElementById(sectionId);
                if (el) el.scrollIntoView({ behavior: "smooth" });
            }, 150);
        } else {
            const el = document.getElementById(sectionId);
            if (el) el.scrollIntoView({ behavior: "smooth" });
        }
    };

    return (
        <motion.nav 
            className="fixed top-4 left-0 right-0 px-8 lg:px-16 z-50 flex items-center justify-between max-w-[1400px] mx-auto"
            initial={{ y: -50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
        >
            {/* Left Logo */}
            <a 
                href="#" 
                onClick={(e) => handleTabChange("home", e)}
                className="w-12 h-12 rounded-full liquid-glass flex items-center justify-center font-heading italic text-2xl text-white select-none hover:bg-white/5 transition-all"
            >
                c
            </a>

            {/* Center Navigation Menu (Desktop Only) */}
            <div className="hidden md:flex items-center gap-1 liquid-glass rounded-full px-1.5 py-1.5">
                <a 
                    href="#" 
                    onClick={(e) => handleTabChange("home", e)}
                    className={`px-3 py-2 text-sm font-medium transition-colors font-body rounded-full ${currentTab === "home" ? "bg-white/10 text-white font-semibold" : "text-white/80 hover:text-white"}`}
                >
                    Home
                </a>
                <a 
                    href="#" 
                    onClick={(e) => handleTabChange("dashboard", e)}
                    className={`px-3 py-2 text-sm font-medium transition-colors font-body rounded-full ${currentTab === "dashboard" ? "bg-white/10 text-white font-semibold" : "text-white/80 hover:text-white"}`}
                >
                    Dashboard
                </a>
                <a 
                    href="#" 
                    onClick={(e) => handleTabChange("art", e)}
                    className={`px-3 py-2 text-sm font-medium transition-colors font-body rounded-full ${currentTab === "art" ? "bg-white/10 text-white font-semibold" : "text-white/80 hover:text-white"}`}
                >
                    Art Generator
                </a>
                <a 
                    href="#" 
                    onClick={(e) => handleScrollToSection("innovation", e)}
                    className="px-3 py-2 text-sm font-medium text-white/80 hover:text-white transition-colors font-body rounded-full"
                >
                    Innovation
                </a>
                
                {/* Claim a Spot / Dashboard CTA button inside the navigation pill */}
                <a 
                    href="#" 
                    onClick={(e) => handleTabChange("dashboard", e)}
                    className="px-4 py-2 text-sm font-semibold bg-white text-black hover:bg-neutral-100 hover:scale-[1.02] active:scale-95 transition-all font-body rounded-full flex items-center gap-1 whitespace-nowrap ml-2"
                >
                    Launch Agent
                    <svg className="h-4 w-4 stroke-current" viewBox="0 0 24 24" fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="7" y1="17" x2="17" y2="7"></line>
                        <polyline points="7 7 17 7 17 17"></polyline>
                    </svg>
                </a>
            </div>

            {/* Right Spacer to balance logo */}
            <div className="w-12 h-12 pointer-events-none opacity-0"></div>
        </motion.nav>
    );
};

window.Navbar = Navbar;

