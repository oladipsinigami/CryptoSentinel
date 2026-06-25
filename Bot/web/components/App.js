const { useState, useEffect } = React;

const App = () => {
    const [currentTab, setCurrentTab] = useState("home");

    // Suppress benign Framer Motion/Babel development warnings in the console
    useEffect(() => {
        const originalError = console.error;
        console.error = (...args) => {
            if (
                typeof args[0] === 'string' &&
                (args[0].includes("React does not recognize the") ||
                 args[0].includes("Failed prop type: The prop") ||
                 args[0].includes("key") ||
                 args[0].includes("Framer Motion") ||
                 args[0].includes("Motion"))
            ) {
                return;
            }
            originalError.apply(console, args);
        };
        return () => {
            console.error = originalError;
        };
    }, []);

    return (
        <div className="relative w-full min-h-screen bg-black text-white selection:bg-white/20">
            {/* Header / Navbar */}
            <window.Navbar currentTab={currentTab} setCurrentTab={setCurrentTab} />
            
            {/* Page Tab Router */}
            {currentTab === "home" && (
                <div id="home-view">
                    <window.Hero setCurrentTab={setCurrentTab} />
                    <window.Capabilities />
                </div>
            )}

            {currentTab === "dashboard" && (
                <div id="dashboard-view">
                    <window.Dashboard />
                </div>
            )}

            {currentTab === "art" && (
                <div id="art-view">
                    <window.ArtGenerator />
                </div>
            )}
        </div>
    );
};

window.App = App;

