export function LineArtLogo() {
  return <svg className="line-art-logo" viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M8 34V14.5L24 6l16 8.5V34L24 42 8 34Z" stroke="currentColor" strokeWidth="1.25"/>
    <path d="M16 29V19l8-4.5 8 4.5v10l-8 4.5-8-4.5Z" stroke="currentColor" strokeWidth="1.15"/>
    <path d="M8 14.5 24 24l16-9.5M24 24v18M16 19l8 5 8-5" stroke="currentColor" strokeWidth="1.05" opacity=".8"/>
    <circle cx="24" cy="24" r="2.1" fill="currentColor"/>
  </svg>;
}

export function LineArtArtwork() {
  return <svg className="line-art-visual" viewBox="0 0 520 370" fill="none" role="img" aria-label="Abstract line-art illustration representing an interconnected intelligent system">
    <defs>
      <linearGradient id="artStroke" x1="74" y1="35" x2="435" y2="340" gradientUnits="userSpaceOnUse"><stop stopColor="#C4E0FF"/><stop offset=".52" stopColor="#76B4FF"/><stop offset="1" stopColor="#72E0C1"/></linearGradient>
      <radialGradient id="artGlow"><stop stopColor="#7DB8FF" stopOpacity=".24"/><stop offset="1" stopColor="#7DB8FF" stopOpacity="0"/></radialGradient>
    </defs>
    <circle cx="270" cy="184" r="155" fill="url(#artGlow)"/>
    <g className="art-orbit art-orbit-one" stroke="url(#artStroke)" strokeWidth="1" opacity=".45">
      <ellipse cx="270" cy="184" rx="205" ry="76" transform="rotate(-27 270 184)"/>
      <ellipse cx="270" cy="184" rx="205" ry="76" transform="rotate(48 270 184)"/>
      <circle cx="270" cy="184" r="129" strokeDasharray="3 8"/>
    </g>
    <g stroke="url(#artStroke)" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round">
      <path className="art-draw" d="M270 87 326 119 326 184 270 216 214 184 214 119 270 87Z"/>
      <path className="art-draw delay-one" d="M270 119 298 135 298 168 270 184 242 168 242 135 270 119Z"/>
      <path d="M270 87V119M326 119 298 135M326 184 298 168M270 216V184M214 184 242 168M214 119 242 135" opacity=".7"/>
      <path d="M270 184 270 254M326 151 390 115M214 151 145 111M270 87 270 45M326 184 389 220M214 184 150 230" opacity=".55"/>
      <path d="M270 254 239 273 239 309 270 327 301 309 301 273 270 254Z" opacity=".8"/>
      <path d="M145 111 124 99M390 115 412 103M150 230 126 242M389 220 414 234M270 45V29" opacity=".55"/>
    </g>
    <g fill="#B9D9FF" stroke="#76B4FF" strokeWidth="1">
      <circle cx="270" cy="184" r="5"/><circle cx="270" cy="45" r="3.5"/><circle cx="145" cy="111" r="3.5"/><circle cx="390" cy="115" r="3.5"/><circle cx="150" cy="230" r="3.5"/><circle cx="389" cy="220" r="3.5"/>
    </g>
    <g stroke="#91C6FF" strokeWidth="1" opacity=".55">
      <path d="M55 285h74l14-14h38M348 57h44l16 16h48M376 295h45l12-12h34M49 75h42l12 12h27"/>
      <path d="M84 299v-28M424 57v-22M467 284v26M107 87V62"/>
    </g>
    <g fill="#8DBEFF" opacity=".75"><circle cx="55" cy="285" r="2"/><circle cx="467" cy="310" r="2"/><circle cx="450" cy="73" r="2"/><circle cx="49" cy="75" r="2"/></g>
  </svg>;
}
