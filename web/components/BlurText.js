const { useState, useEffect, useRef } = React;
const { motion } = window.Motion;

const BlurText = ({ text, className }) => {
    const [inView, setInView] = useState(false);
    const containerRef = useRef(null);

    useEffect(() => {
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setInView(true);
                    observer.unobserve(entry.target);
                }
            },
            { threshold: 0.1 }
        );

        if (containerRef.current) {
            observer.observe(containerRef.current);
        }

        return () => {
            if (containerRef.current) {
                observer.unobserve(containerRef.current);
            }
        };
    }, []);

    const words = text.split(" ");

    return (
        <p
            ref={containerRef}
            className={className}
            style={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "center",
                rowGap: "0.1em"
            }}
        >
            {words.map((word, i) => (
                <motion.span
                    key={i}
                    style={{
                        display: "inline-block",
                        marginRight: "0.28em"
                    }}
                    initial={{ filter: "blur(10px)", opacity: 0, y: 50 }}
                    animate={inView ? {
                        filter: ["blur(10px)", "blur(5px)", "blur(0px)"],
                        opacity: [0, 0.5, 1],
                        y: [50, -5, 0]
                    } : {}}
                    transition={inView ? {
                        duration: 0.7,
                        times: [0, 0.5, 1],
                        ease: "easeOut",
                        delay: (i * 100) / 1000
                    } : {}}
                >
                    {word}
                </motion.span>
            ))}
        </p>
    );
};

window.BlurText = BlurText;
