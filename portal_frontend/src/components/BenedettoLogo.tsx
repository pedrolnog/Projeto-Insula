"use client";

interface BenedettoLogoProps {
  variant?: "light" | "dark";
  size?: "sm" | "md" | "lg";
  className?: string;
}

/**
 * Logotipo arquitetônico oficial da BENEDETTO:
 * Representa "A Ponte" (Ligação horizontal + os 2 Pilares verticais formando os dois 'T' de BENEDETTO).
 */
export function BenedettoLogo({
  variant = "light",
  size = "md",
  className = "",
}: BenedettoLogoProps) {
  const strokeColor = variant === "light" ? "#FFFFFF" : "#111215";

  const dimensions = {
    sm: "w-36 h-auto",
    md: "w-52 h-auto",
    lg: "w-64 sm:w-72 h-auto",
  }[size];

  return (
    <svg
      viewBox="0 0 360 110"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${dimensions} select-none ${className}`}
      aria-label="BENEDETTO"
    >
      {/* Linha Horizontal (Ligação / Tabuleiro da Ponte) */}
      <rect x="10" y="54" width="340" height="8" fill={strokeColor} />

      {/* Dois Pilares Verticais (Os dois T's de BENEDETTO) */}
      <rect x="260" y="6" width="8" height="94" fill={strokeColor} />
      <rect x="298" y="6" width="8" height="94" fill={strokeColor} />

      {/* Tipografia B E N E D E [||] O alinhada sob a ponte */}
      <g
        fill={strokeColor}
        style={{
          fontFamily: "var(--font-montserrat), sans-serif",
          fontSize: "23px",
          fontWeight: 500,
        }}
      >
        <text x="26" y="96">
          B
        </text>
        <text x="64" y="96">
          E
        </text>
        <text x="101" y="96">
          N
        </text>
        <text x="142" y="96">
          E
        </text>
        <text x="180" y="96">
          D
        </text>
        <text x="220" y="96">
          E
        </text>
        <text x="319" y="96">
          O
        </text>
      </g>
    </svg>
  );
}
