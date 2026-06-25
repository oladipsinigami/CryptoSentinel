const { useEffect, useRef } = React;

const FadingVideo = ({ src, className, style }) => {
    const videoRef = useRef(null);
    const fadingOutRef = useRef(false);
    const rafIdRef = useRef(null);

    const fadeTo = (targetOpacity, durationMs) => {
        const video = videoRef.current;
        if (!video) return;

        // Cancel previous animation frame if one is active
        if (rafIdRef.current) {
            cancelAnimationFrame(rafIdRef.current);
        }

        // Get starting opacity, fallback to 0 if not set
        const startOpacity = parseFloat(video.style.opacity) || 0;
        let startTime = null;

        const animate = (timestamp) => {
            if (!startTime) startTime = timestamp;
            const elapsed = timestamp - startTime;
            const progress = Math.min(elapsed / durationMs, 1);

            // Linear interpolation of opacity
            const currentOpacity = startOpacity + (targetOpacity - startOpacity) * progress;
            video.style.opacity = currentOpacity;

            if (progress < 1) {
                rafIdRef.current = requestAnimationFrame(animate);
            } else {
                rafIdRef.current = null;
            }
        };

        rafIdRef.current = requestAnimationFrame(animate);
    };

    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        // Initialize opacity to 0
        video.style.opacity = "0";

        const handleLoadedData = () => {
            video.style.opacity = "0";
            video.play().catch(err => console.log("Video play interrupted:", err));
            fadeTo(1, 500);
        };

        const handleTimeUpdate = () => {
            if (!video.duration) return;
            const timeRemaining = video.duration - video.currentTime;

            // Trigger fade out 0.55s before video ends
            if (!fadingOutRef.current && timeRemaining <= 0.55 && timeRemaining > 0) {
                fadingOutRef.current = true;
                fadeTo(0, 500);
            }
        };

        const handleEnded = () => {
            video.style.opacity = "0";
            
            // Loop manually with a 100ms gap
            setTimeout(() => {
                if (!videoRef.current) return;
                video.currentTime = 0;
                video.play().catch(err => console.log("Video loop play interrupted:", err));
                fadingOutRef.current = false;
                fadeTo(1, 500);
            }, 100);
        };

        video.addEventListener('loadeddata', handleLoadedData);
        video.addEventListener('timeupdate', handleTimeUpdate);
        video.addEventListener('ended', handleEnded);

        // Force play if source changes or is already cached
        if (video.readyState >= 2) {
            handleLoadedData();
        }

        return () => {
            video.removeEventListener('loadeddata', handleLoadedData);
            video.removeEventListener('timeupdate', handleTimeUpdate);
            video.removeEventListener('ended', handleEnded);
            if (rafIdRef.current) {
                cancelAnimationFrame(rafIdRef.current);
            }
        };
    }, [src]);

    return (
        <video
            ref={videoRef}
            src={src}
            className={className}
            style={{ ...style, transition: 'none' }} // Ensure no CSS transition interferes
            autoPlay
            muted
            playsInline
            preload="auto"
        />
    );
};

// Export to global scope for Babel standalone
window.FadingVideo = FadingVideo;
