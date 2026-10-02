#!/usr/bin/env python3
"""Write paste-ready image prompts for the 32 design directions.

Skips a card when that style already has the image, and skips THE DEVIL,
whose prompt already lives in design/design.md.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "design"
MD = DESIGN / "design.md"

# id, numeral, title, scene with optional {who}
CARDS = [
    (
        "the-fool",
        "0",
        "THE FOOL",
        "{who} steps to the edge of a cliff, one foot still raised. One hand holds a white rose, the other a staff with a small bundle. A small dog looks up. A bright sun and distant mountains sit behind.",
    ),
    (
        "the-magician",
        "I",
        "THE MAGICIAN",
        "{who} stands at a table, one hand raised and the other pointing down. An infinity sign floats above the head. On the table are a cup, a wand, a sword, and a pentacle. Roses and lilies grow at the edge of the table.",
    ),
    (
        "the-high-priestess",
        "II",
        "THE HIGH PRIESTESS",
        "{who} sits still between a dark pillar and a light pillar, half hidden. A scroll lies in the lap, a cross on the chest, and a crescent at the feet. A veil patterned with pomegranates hangs behind.",
    ),
    (
        "the-empress",
        "III",
        "THE EMPRESS",
        "{who} sits among wheat, a crown of stars on the head and a scepter in one hand. A heart-shaped shield bears the sign of Venus. A waterfall and cypresses are behind, with pomegranates and roses around the seat.",
    ),
    (
        "the-emperor",
        "IV",
        "THE EMPEROR",
        "{who} sits square and still on a stone throne carved with ram heads, an ankh scepter in one hand and an orb in the other. Armor shows under a long cloak. Barren mountains fill the background.",
    ),
    (
        "the-hierophant",
        "V",
        "THE HIEROPHANT",
        "{who} sits between two pillars, a triple crown on the head, one hand raised in blessing and the other holding a staff with a triple cross. Two attendants kneel and look up. Crossed keys lie at the feet.",
    ),
    (
        "the-lovers",
        "VI",
        "THE LOVERS",
        "{who} hovers with arms spread above a man and a woman who stand apart and have not chosen. He is before a tree wound by a serpent, she before a tree of fruit. A mountain and a sun are behind.",
    ),
    (
        "the-chariot",
        "VII",
        "THE CHARIOT",
        "{who} stands in a chariot under a canopy of stars, a wand in one hand. A black sphinx and a white sphinx draw it. A walled city is behind, and crescents rest at the shoulders.",
    ),
    (
        "strength",
        "VIII",
        "STRENGTH",
        "{who} calmly closes a lion's mouth, the hands gentle rather than forcing. An infinity sign floats above the head. A garland of flowers circles the figure and the lion.",
    ),
    (
        "the-hermit",
        "IX",
        "THE HERMIT",
        "{who} stands alone on a high ledge, old and hooded, a staff in one hand. The lantern lights only the next step. A small star burns inside the lantern, and the rest of the mountain is dark.",
    ),
    (
        "wheel-of-fortune",
        "X",
        "WHEEL OF FORTUNE",
        "No human rider. A great wheel turns in the sky. A sphinx with a sword sits at the top, a jackal climbs one side, and a snake descends the other. An angel, an eagle, a lion, and a bull occupy the four corners. Letters and symbols ring the wheel.",
    ),
    (
        "justice",
        "XI",
        "JUSTICE",
        "{who} sits frontally between two pillars, a sword held upright in one hand and scales level in the other. A crown is on the head. The pose is calm and exact.",
    ),
    (
        "the-hanged-man",
        "XII",
        "THE HANGED MAN",
        "{who} is shown head-down in a chosen, peaceful pause, one foot resting on a living wooden tau, the other leg crossed, the hands behind the back. A halo circles the head. The face is calm. No injury, no blood, no distress, no rope.",
    ),
    (
        "death",
        "XIII",
        "DEATH",
        "{who} rides a white horse and carries a dark banner with a single white rose. A crown lies in the dust, an elder stands, a child kneels, and a sun rises between two towers. The ending opens onto what comes next.",
    ),
    (
        "temperance",
        "XIV",
        "TEMPERANCE",
        "{who} pours from one cup into another in a single steady stream. One foot is in a pool and the other on land. Irises grow by the water. A path leads to a mountain crowned with light.",
    ),
    (
        "the-tower",
        "XVI",
        "THE TOWER",
        "Lightning strikes the crown from a tall stone tower. {who} falls through the air with a second figure, and fire shows in the windows. The clouds are dark and the ground is bare rock.",
    ),
    (
        "the-star",
        "XVII",
        "THE STAR",
        "{who} kneels by a pool and pours from two jugs, one into the water and one onto the land. One great star and seven smaller stars shine above. A bird sits in a tree, with low mountains on the horizon.",
    ),
    (
        "the-moon",
        "XVIII",
        "THE MOON",
        "A large moon hangs between two towers, its face only half clear. A dog and a wolf stand on either side of a long path. A crayfish rises from a pool in the foreground. Drops of light fall. The path is dim, not fully dark.",
    ),
    (
        "the-sun",
        "XIX",
        "THE SUN",
        "A child rides a white horse beneath a huge sun whose rays are straight and wavy by turns. Sunflowers stand in front of a low wall. A banner streams behind. Everything in the picture is plainly visible.",
    ),
    (
        "judgement",
        "XX",
        "JUDGEMENT",
        "{who} leans from a cloud and blows a trumpet, a flag hanging from the trumpet. Below, figures rise from open coffins with their arms lifted, mountains behind them. The call is being answered.",
    ),
    (
        "the-world",
        "XXI",
        "THE WORLD",
        "{who} dances inside a great wreath, a wand in each hand, a sash flowing. An angel, an eagle, a lion, and a bull occupy the four corners. The pose is both moving and complete.",
    ),
]

# Noun phrase that can take a verb. Omitted styles have hand-written scenes.
WHO = {
    "editorial-luxury": "A fashion model in ivory silk and black",
    "neo-deco": "A symmetrical figure in black lacquer and brass",
    "cyber-mysticism": "A pale figure wrapped in translucent glass",
    "brutalist-graphic": "A faceted cut-paper figure",
    "surreal-photography": "A photographed person",
    "japanese-contemporary-poster": "A flat ink figure",
    "neo-symbolism": "A monumental figure",
    "luxury-ui": "A luminous figure on a glass panel",
    "wayang-kulit": "A tall leather puppet in profile",
    "greek-sculpture": "A white marble statue",
    "cubism": "A figure broken into flat color planes",
    "plastic-model-diorama": "A painted plastic figure",
    "french-doll": "An antique bisque doll with glass eyes and ringlets",
    "botanical-art": "A figure drawn at botanical scale",
    "unkei-kaikei": "A wooden statue with inlaid crystal eyes",
    "stained-glass": "A figure of jewel-colored glass",
    "tile-mosaic": "A figure built from small tiles",
    "art-nouveau": "A figure with long curling hair and flowing cloth",
    "classic-tarot": "A flat, crudely drawn figure",
    "ancient-egypt": "A profile figure in linen and a gold collar",
    "engraving": "A figure of dense burin line",
    "mezzotint": "A figure scraped out of black",
    "colored-pencil": "A figure of layered pencil strokes",
    "watercolor": "A figure blooming from a thin wash",
    "sumi-e": "An ink figure with a dry-brush edge",
}

LOCK = {
    "editorial-luxury": "Black, ivory, and metallic gold only, inside a thin gold frame. Props read as jewelry in a fashion campaign.",
    "neo-deco": "Black lacquer, brass, and one deep jewel tone. Stepped forms and bilateral symmetry. No whiplash curves.",
    "cyber-mysticism": "Dark glass, a few holographic rings, and thin gold geometry. Few objects, elegant rather than cluttered.",
    "brutalist-graphic": "Huge block letters spell {title}, one word in red. Black, red, and cream. The poster is asymmetrical, with ink grain and misregistration.",
    "surreal-photography": "Real cloth, stone, and metal, photographed in impossible architecture. Restrained palette, gallery light.",
    "japanese-contemporary-poster": "Flat ink and a little gold leaf. Asymmetric, with large areas of bare paper. Red, black, cream, and gold only.",
    "neo-symbolism": "Few ornaments. Muted slate, bone, and dull gold. Each object is one clear symbol in an almost empty landscape.",
    "luxury-ui": "Dark glass panels, gold hairlines, and one soft glow. An instrument, not a painted relic.",
    "wayang-kulit": "Elongated arms, punched gold filigree, crimson and turquoise. Warm light behind the screen.",
    "greek-sculpture": "Photographed in a temple. Gold leaf on white stone, chisel marks left visible. A statue, not an illustration.",
    "cubism": "Ochre, teal, brick, black, and cream. Canvas weave stays visible. No smooth surface and no single light source.",
    "plastic-model-diorama": "Glue seams and brush paint stay visible on the kit. The wooden base carries the nameplate.",
    "french-doll": "Porcelain, silk, lace, and ribbons. Candlelight. Black, ivory, and burgundy. Ball joints visible. No gore.",
    "botanical-art": "Fine ink and watercolor on cream paper. Flowers, leaves, and fruit are drawn with the same precision as the figure, inside a hairline border.",
    "unkei-kaikei": "Worn mineral pigment and deep chisel folds. A flame halo only where the card has a glory. Cracks stay visible. A real statue, photographed.",
    "stained-glass": "Lead lines divide every shape. Ruby, cobalt, gold, and emerald glow because the light comes through the glass.",
    "tile-mosaic": "Grout lines stay visible. Gold, cream, black, and terracotta tiles. Star medallions occupy the corners.",
    "art-nouveau": "Whiplash curves, lilies, and vines grow through the border. Peacock green, cream, and gold. No stepped brass and no sunburst.",
    "classic-tarot": "Flat mineral color, a crude outline, worn and foxed paper, and a plain black rule.",
    "ancient-egypt": "Flat profile on aged papyrus. No perspective and no modeled shading. Mineral red, turquoise, gold, and black, with a lotus border.",
    "engraving": "Warm laid paper and burin line only. No color. An ornamental border with corner roundels.",
    "mezzotint": "The lights are scraped out of a rocked black plate. Sepia on warm paper. No crosshatching and no drawn outline.",
    "colored-pencil": "Directional strokes on toothy paper. Red, indigo, ochre, and gold. No airbrush smoothness.",
    "watercolor": "Blooms, backruns, and granulation. Indigo, burnt sienna, and a little gold. The paper shows through at the edges.",
    "sumi-e": "Black and gray only, plus two small red seals. Splatter and dry brush. Most of the ground is blank paper.",
}

# Full scene paragraphs for styles that cannot share a human figure.
SPECIAL = {
    "minimal-geometric": {
        "the-fool": "A white circle, a broken horizontal for the cliff, a staff reduced to one line, a small circle for the rose, and a triangle for the dog. The raised foot is a single step off the grid.",
        "the-magician": "A vertical bar for the body, one arm up and one down, and an infinity made of two circles. Four tokens sit on a ruled table: cup, wand, sword, and disc. Roses and lilies are two repeated marks.",
        "the-high-priestess": "A seated triangle between a black bar and a white bar. A small scroll, a cross, and a crescent. A veil is a row of pomegranate circles. Large empty ground.",
        "the-empress": "A seated curve, a crown of twelve small stars, a scepter as one line, and a heart shield with the sign of Venus. Wheat is a row of strokes. A waterfall is three verticals.",
        "the-emperor": "A square seated block on a throne of ram-head angles. An ankh and a circle. Mountains are a measured zigzag. No texture except a faint paper grain.",
        "the-hierophant": "A seated figure reduced to a triple crown of three bars, one hand a vertical, a staff of three crosses. Two small kneeling marks. Two crossed keys.",
        "the-lovers": "An angel reduced to a triangle with a span of arms. Two standing bars below, apart. One tree is a spiral, the other a column of dots. A mountain is one peak. The gap between the two figures is the point.",
        "the-chariot": "A rectangle chariot, a canopy of one star, a vertical rider. Two opposed sphinx shapes, black and white. A city is a row of squares.",
        "strength": "A standing curve and a lion reduced to a circle and a mane of short strokes, the hands meeting the mouth. An infinity of two circles above. A garland is a ring of small marks.",
        "the-hermit": "A hooded vertical on a stepped peak. A lantern is a small square holding one star, lighting only the next horizontal. The rest of the sheet stays empty.",
        "wheel-of-fortune": "A circle on the grid, no person. A sphinx mark at the top, a jackal mark climbing, a snake as an S. Four corner glyphs: angel, eagle, lion, bull. Letters become small ticks around the rim.",
        "justice": "A frontal seated block between two pillars. A vertical sword and a level pair of scales. A crown is three short bars.",
        "the-hanged-man": "A tau of two lines. A figure shown head-down, one foot on the upright, the other leg a crossing stroke, a circle halo. The face is a blank oval. A chosen, peaceful pause. No injury and no rope.",
        "death": "A horse reduced to an arc, a rider as a vertical, a banner with one rose circle. A fallen crown, a standing bar, a small kneeling mark, and a rising sun between two towers.",
        "temperance": "One figure as a narrow vertical pouring a single arc between two cups. One foot on a water line, one on a ground line. Irises are three strokes. A path is a ruled line to a triangle mountain.",
        "the-tower": "A tall rectangle hit by a zigzag. A crown shape leaves the top. Two small figures are falling marks. Windows are squares, two of them solid.",
        "the-star": "A kneeling angle by a pool circle, two jugs, two pour-lines. One large star and seven small ones. A bird is a small V in a tree of three lines.",
        "the-moon": "A crescent between two towers. A path is one line. A dog and a wolf are two opposed marks. A crayfish is a small fan at the bottom. Drops are a few dots. Wide empty ground.",
        "the-sun": "A large circle with straight and wavy rays. A small rider on a horse of two arcs. Four sunflower circles and a low wall of one line.",
        "judgement": "A trumpet as a cone in a cloud bar, a small flag. Three rising figures over open rectangles. Mountains are a low zigzag.",
        "the-world": "A figure in an oval wreath, two short wands. Four corner marks: angel, eagle, lion, bull. The center stays open.",
    },
    "glass-and-chrome": {
        "the-fool": "A clear glass figure is caught mid-step at the edge of a smoked plinth, a gold rose and a thin rod in the hands, a small glass dog at the foot. A gold disc sun. No face, no costume, mirrored floor.",
        "the-magician": "A chrome figure stands at a glass table, one arm raised and one lowered. Four objects, cup, wand, sword, and disc, are small gold and glass tokens. An infinity ring hangs in the air. No face.",
        "the-high-priestess": "A smoked-glass figure sits between a black glass pillar and a clear one. A scroll, a small cross, and a crescent are the only gold marks. A veil is a faint etched screen. No face.",
        "the-empress": "A clear figure sits among gold wheat rods. A star crown and a heart shield with the sign of Venus are polished metal. A glass waterfall and a few gold roses. No face.",
        "the-emperor": "A black-chrome seated figure on a throne with ram-head angles, an ankh and a sphere in the hands. Glass mountains behind. No face and no costume.",
        "the-hierophant": "A tall chrome figure with a triple crown of stacked rings sits between two glass pillars, one hand raised. Two smaller featureless figures kneel. Crossed gold keys lie on the floor.",
        "the-lovers": "A suspended glass figure with arms spread hangs above two featureless figures who stand apart. Two trees, one with a gold spiral and one with glass fruit. The space between them stays empty.",
        "the-chariot": "A chrome charioteer under a glass canopy of stars. Two sphinx sculptures, one black and one clear, face opposite ways. A gold wand. A city of glass blocks behind.",
        "strength": "A clear figure and a chrome lion, her hands at its mouth, the gesture quiet. A gold infinity ring above. A few glass flowers. No faces.",
        "the-hermit": "A smoked-glass hooded figure on a dark plinth, a staff, and a small lantern that lights only the next step. The rest of the gallery falls off into black. No face.",
        "wheel-of-fortune": "No human figure. A large gold-and-glass wheel stands in the gallery. A chrome sphinx at the top, a jackal form and a snake of tubing, and four small corner sculptures. Mirrored floor.",
        "justice": "A chrome seated figure between two glass pillars, a vertical glass sword and level gold scales. No face.",
        "the-hanged-man": "A featureless glass figure is shown head-down, one foot resting on a dark metal tau, the other leg crossed, a thin gold halo. Soft light, mirrored floor, no face. A chosen, peaceful pause. No injury and no rope.",
        "death": "A black-chrome rider on a clear glass horse, a dark banner with one white glass rose. A fallen crown, a standing figure, a small kneeling figure, and a low gold sun between two glass towers.",
        "temperance": "A tall clear figure pours a stream between two glass cups. One foot in a shallow pool, one on stone. A few iris blades. A path of light to a glass mountain.",
        "the-tower": "A smoked-glass tower, a gold crown struck off by a white bolt. Two featureless figures fall. Fire is a small red glow in the windows, the only warm note. Mirrored floor.",
        "the-star": "A clear kneeling figure pours from two jugs into a pool and onto the floor. One large star and seven small ones hang as glass lamps. A small bird form in a metal tree.",
        "the-moon": "A pale glass moon between two dark towers. A chrome dog and a smoked-glass wolf flank a dim path. A small crayfish form in a black pool. Light is low, not absent.",
        "the-sun": "A child-scale clear figure on a white glass horse, under a large gold sun with straight and wavy rays. Four sunflower discs and a low glass wall. The room is brightly lit.",
        "judgement": "A chrome angel form in a glass cloud blows a trumpet with a small flag. Below, featureless figures rise from open glass boxes. No faces.",
        "the-world": "A chrome figure turns inside a glass wreath, a slim rod in each hand. Four small sculptures occupy the corners: angel, eagle, lion, bull. Soft gallery light.",
    },
    "gear-engine-robotics": {
        "the-fool": "A light iron walker steps off a cliff of gears, a brass rose in one gripper and a rod with a bundle on the back. A small dog-machine looks up. A sun of brass teeth. No skin.",
        "the-magician": "A standing engine at a work of gears, one arm raised and one lowered, an infinity of two linked rings above. Four tools on the table: cup, wand, sword, and toothed disc. No skin.",
        "the-high-priestess": "A seated machine between a dark column and a bright one, a scroll of punched plate in the lap and a crescent lamp at the feet. A screen of pomegranate gears behind. No skin.",
        "the-empress": "A seated engine among brass wheat, a crown of star-gears and a scepter. A heart plate bears the sign of Venus. A waterfall of chain and a few bolted roses. No skin.",
        "the-emperor": "A heavy seated engine on a throne of ram-head castings, an ankh rod and a sphere. Armor is boiler plate. Mountains are stacked housings. No skin.",
        "the-hierophant": "A tall machine with a triple crown of rings sits between two columns, one hand raised, a staff of three crosses. Two smaller machines kneel. Crossed keys on the floor. No skin.",
        "the-lovers": "A winged engine hovers above two machines that stand apart and are not joined. One tree of tubing ends in a serpent coil, the other in fruit-shaped housings. The gap is empty. No skin.",
        "the-chariot": "An armored engine stands in a chariot of plate under a canopy of star-gears. A black sphinx-machine and a white one pull in harness. A city of stacks behind. No skin.",
        "strength": "A slender engine calmly holds the jaws of a lion-machine. An infinity of two rings above. A garland of small gears. No struggle and no skin.",
        "the-hermit": "A lone hooded engine on a high gantry, a staff, and a lantern that lights only the next tread. A small star filament inside. The rest of the cathedral of machines is dark. No skin.",
        "wheel-of-fortune": "No human form. A great gear turns, a sphinx-engine with a sword at the top, a jackal-machine climbing, a snake of cable descending. Four corner engines: angel, eagle, lion, bull.",
        "justice": "A seated engine between two columns, a vertical blade and level scales. The crown is a ring of bolts. No skin.",
        "the-hanged-man": "An engine is shown head-down, one foot resting on a tau of beams, the other leg crossed, a halo ring of brass. The pose is a chosen, still pause. No skin. No injury and no rope.",
        "death": "A black engine rides a white-metal horse and carries a dark banner with one brass rose. A fallen crown gear, a standing machine, a small kneeling machine, and a rising sun gear between two towers. No skin.",
        "temperance": "A winged engine pours a stream of oil between two cups. One foot in a channel, one on plate. Iris-shaped vanes. A path to a mountain of housings. No skin.",
        "the-tower": "Lightning splits the crown gear from a tower of boilers. Two machines fall. Fire in the ports. Rivets and smoke. No skin.",
        "the-star": "A kneeling engine pours from two jugs, one into a sump and one onto the floor. One great lamp-star and seven smaller ones. A bird-machine in a tree of pipe. No skin.",
        "the-moon": "A dim lamp-moon between two towers. A dog-machine and a wolf-machine on a dark catwalk. A crayfish of plates rises from a sump. The way is poorly lit, not black. No skin.",
        "the-sun": "A small engine rides a white-metal horse under a huge sun gear with straight and wavy rays. Four sunflower gears and a low wall. Furnace-bright. No skin.",
        "judgement": "An angel-engine in steam blows a trumpet with a flag. Below, machines rise out of open cases. No skin.",
        "the-world": "An engine turns inside a wreath of laurel-shaped gears, a rod in each hand. Four corner machines: angel, eagle, lion, bull. No skin.",
    },
    "rorschach": {
        "the-fool": "One mirrored blot suggests a cliff, a raised foot, a rose, a staff, and a small dog. A sun is a pale bloom. Nothing else is legible.",
        "the-magician": "A standing blot with one arm up and one down, an infinity of two lobes above, and four small marks on a table: cup, wand, sword, disc.",
        "the-high-priestess": "A seated blot between two pillars, a crescent at the base, a veil of repeated seeds behind. The center stays pale, as if hidden.",
        "the-empress": "A seated blot in a field of wheat-like strokes, a star crown, a heart, and a few fruit blooms. Wide empty margin.",
        "the-emperor": "A blocky seated blot on a throne, ram horns only as two curls, mountains as a low stain. Almost no contour.",
        "the-hierophant": "A tall blot with a triple crown, two small kneeling blots, and a pair of crossed keys. The blessing hand is one upward drip.",
        "the-lovers": "A wide blot above two separate standing blots. Two trees, one coiled and one dotted. The gap between the pair is blank paper.",
        "the-chariot": "A canopy and a standing blot over a rectangular mass. Two opposed animal blots, one denser than the other.",
        "strength": "A standing blot meeting a maned blot at the mouth. A small infinity of two lobes above. The contact is quiet, not a fight.",
        "the-hermit": "A narrow hooded blot on a peak, a tiny lantern star lighting one step. Most of the sheet is untouched.",
        "wheel-of-fortune": "A ring-shaped blot. A mass at the top, a climbing shape, a descending S. Four corner blots. No body in the middle.",
        "justice": "A frontal blot with a vertical sword-drip and a level pair of pans. Two pillar stains.",
        "the-hanged-man": "A head-down blot, one foot resting on a tau, one leg crossed, a round halo that is only a thinner ring of ink. A chosen, peaceful pause. No injury and no rope.",
        "death": "A horse blot and a rider, a banner reduced to a bar with one rose spot. A fallen shape, a standing shape, a small kneeling shape, a pale sun.",
        "temperance": "A tall blot pouring one bridge of ink between two cups. A water line and a land line. A path is a thin tail of wash.",
        "the-tower": "A vertical blot split by a lightning drip. A crown shape breaks off. Two small blots fall. Windows are holes in the ink.",
        "the-star": "A kneeling blot by a pool, two pours, one large star bloom and seven small ones. A bird is a flick in a tree stain.",
        "the-moon": "A moon blot between two towers. Two animal blots face each other across a pale path. A small crayfish bloom at the bottom. The center path is the paper showing through.",
        "the-sun": "A large sun bloom with rays as thinner flicks. A small rider blot. Four flower blooms and a wall that is one dry edge.",
        "judgement": "A trumpet blot in a cloud, a flag flick. Below, figures rise out of box-shaped reserves of bare paper.",
        "the-world": "A dancing blot inside a wreath that is a ring of smaller blooms. Four corner blots. The middle of the wreath is almost empty.",
    },
    "ruler-compass-pen": {
        "the-fool": "The cliff is a ruled break, the youth a construction of arcs and straight lines caught mid-step, the rose a compass flower, the dog a small constructed animal. A sun is a circle with its center mark left in.",
        "the-magician": "A standing figure of ruled limbs, one arm up and one down, the infinity two linked compass circles. The table holds a cup, a wand, a sword, and a pentacle, each drawn with center marks.",
        "the-high-priestess": "A seated figure of arcs between two ruled pillars. Scroll, cross, and crescent are pure geometry. The veil is a row of compass pomegranates.",
        "the-empress": "A seated figure, a crown of twelve circles, a ruled scepter, and a heart drawn with compass and straightedge bearing the sign of Venus. Wheat is a fan of lines.",
        "the-emperor": "A seated figure on a throne, ram heads as paired arcs, an ankh and a circle in the hands. Mountains are regulating triangles.",
        "the-hierophant": "A seated figure, a triple crown of three arcs, a staff of three crosses, two smaller constructed attendants, and crossed keys. Construction lines stay visible.",
        "the-lovers": "An angel of arcs above two figures who do not touch. One tree is a spiral construction, the other a column of circles. The gap between them is unmarked paper.",
        "the-chariot": "A chariot of rectangles under a canopy of one star. Two sphinxes, constructed in mirror, one noted as black only by a denser line. A city is a row of squares.",
        "strength": "A standing figure and a lion, both constructions, the hands meeting the mouth. The infinity is two circles. A garland is a ring of small arcs.",
        "the-hermit": "A hooded figure on a triangle peak. The lantern is a square around a star, and only the next step is drawn firmly. The rest is faint construction.",
        "wheel-of-fortune": "A circle with its center left visible. No person. A sphinx, a jackal, and a snake reduced to arcs, and four corner constructions. Ticks around the rim stand in for letters.",
        "justice": "A frontal seated construction between two pillars. The sword is a ruled vertical. The scales are two equal arcs on a level line.",
        "the-hanged-man": "A tau of two ruled lines. A head-down figure, one foot on the upright, the free leg a crossing line, the halo a circle. A chosen, peaceful pause. Every center mark remains. No injury and no rope.",
        "death": "A horse of arcs and a rider of straight lines, a banner with one rose drawn by the compass. A fallen crown, a standing figure, a small kneeling figure, and a rising circle between two towers.",
        "temperance": "A standing figure pouring a single arc between two cups. One foot on a water line, one on a ground line. A path of ruled segments to a triangle mountain.",
        "the-tower": "A tall rectangle, a lightning path of straight segments, a crown of arcs leaving the top. Two small falling constructions. Windows are squares.",
        "the-star": "A kneeling construction by a circle pool, two jugs, two pour-arcs. One large star of intersecting lines and seven smaller ones. A bird of two strokes in a constructed tree.",
        "the-moon": "A circle moon between two towers. A dog and a wolf as paired constructions. A path is one ruled line. A crayfish is a fan of arcs. The path is drawn lighter than the towers.",
        "the-sun": "A large circle with alternating straight and wavy rays, the waves as compass arcs. A small rider on a constructed horse. Four flower circles and a ruled wall.",
        "judgement": "A trumpet of cones and a flag of triangles in a cloud of arcs. Figures rise from open rectangles. Mountains are regulating triangles.",
        "the-world": "A figure of arcs inside a wreath of repeated leaves, two short wands. Four corner constructions: angel, eagle, lion, bull. Construction lines are not erased.",
    },
    "suit-and-dress": {
        "the-fool": "A young man in a black suit and white shirt steps off a marble ledge, one foot raised, a white rose in one hand and a slim cane with a small wrapped bundle in the other. A small white dog looks up. A gold sun and a distant city.",
        "the-magician": "A man in a black suit stands at a marble table, one hand raised and one lowered. On the table, a glass, a pen, a letter opener, and a coin. An infinity is a thin gold line in the air. Roses and lilies in one vase.",
        "the-high-priestess": "A woman in a column of satin sits between a black marble pillar and a white one, a folded paper in her lap and a crescent pin at her hem. A veil with a pomegranate pattern hangs behind. She is only half shown.",
        "the-empress": "A woman in a satin gown sits among wheat, a star tiara and a slim gold scepter. A heart brooch bears the sign of Venus. Roses, pomegranates, and a waterfall behind her.",
        "the-emperor": "A man in a black three-piece suit sits on a stone chair carved with ram heads, mountains behind him. A slim gold staff and a small orb. No armor and no crown, only the square pose.",
        "the-hierophant": "An older man in a black suit sits between two pillars and raises one hand. Two people in suits kneel. A triple staff leans at his side, and crossed keys are mounted on the wall.",
        "the-lovers": "A woman in a white gown stands above a man in a black suit and a woman in a satin dress who have not stepped toward each other. He is by one tree, she by another. A mountain shows through a tall window.",
        "the-chariot": "A man in a black suit stands in an open black-and-white car under a canopy of small stars, a slim cane in one hand. Two sphinx hood ornaments, one black and one white. A city behind.",
        "strength": "A woman in a white gown rests her hands on a lion's mouth, calm rather than fighting. A thin gold infinity hangs above them. A few flowers. Studio marble.",
        "the-hermit": "An older man in a black overcoat stands on a dark stair with a cane. His small lantern lights only the next step. The rest of the hall is out of the light.",
        "wheel-of-fortune": "No person. A large gold wheel stands in a marble gallery. A sphinx sculpture with a sword at the top, a jackal and a snake as metal reliefs, and four corner reliefs: angel, eagle, lion, bull.",
        "justice": "A woman in a black suit sits between two marble pillars, a dress sword upright in one hand and level scales in the other. Even studio light.",
        "the-hanged-man": "A man in a black suit is shown head-down in a chosen, peaceful pause, one foot resting on a wooden beam, the other leg crossed, hands behind him, expression calm. A thin gold ring behind the head. No distress, no injury, no rope.",
        "death": "A pale person in a black suit rides a white horse and carries a black banner with one white rose. A crown lies on the marble, an older man in a suit stands, a child kneels, and a low sun shows between two towers.",
        "temperance": "A woman in a white gown pours from one glass into another in a steady stream. One foot is in a shallow pool, the other on stone. Irises, and a path toward a bright doorway.",
        "the-tower": "Lightning knocks a gold crown-like finial off a stone tower. A man in a black suit and a woman in a dark dress fall. Fire in the windows. No costume beyond the clothes.",
        "the-star": "A woman in a simple white dress kneels by a pool and pours from two pitchers, one into the water and one onto the ground. One large star and seven smaller ones. A bird in a tree.",
        "the-moon": "A dim moon between two towers. A dog and a wolf on either side of a wet path. A crayfish in the foreground pool. The path is hard to see, not gone.",
        "the-sun": "A child in a white shirt rides a white horse under a huge sun with straight and wavy rays. Four sunflowers and a low wall. A banner. The whole scene is evenly lit.",
        "judgement": "A woman in a white gown leans from a high opening and blows a trumpet with a small flag. Below, people in suits rise through open rectangular hatches, arms up.",
        "the-world": "A woman in a satin dress dances inside a green wreath, a slim rod in each hand. Four sculptures occupy the corners: angel, eagle, lion, bull. Marble and a gold frame.",
    },
    "chess-pieces": {
        "the-fool": "A small white pawn tilts at the edge of the board as if stepping off. A rose is carved on it, a tiny dog-piece looks up, and a sun token sits behind. Other pieces recede. No human bodies.",
        "the-magician": "A tall white piece stands behind four tokens in a row: a cup, a wand, a sword, and a coin. An infinity is inlaid on its head. Roses and lilies are carved on the base. No human bodies.",
        "the-high-priestess": "A white queen stands between two rook pillars, one black and one white. A scroll tile, a small cross, and a crescent token. A screen of carved seeds behind. No human bodies.",
        "the-empress": "A white queen with a crown of small stars sits among wheat-colored squares. A heart on the base bears the sign of Venus. Tiny carved roses and a waterfall in the distance of the board. No human bodies.",
        "the-emperor": "A black king on a throne base carved with ram heads, a staff and a sphere. The far rank is a mountain of stacked pieces. No human bodies.",
        "the-hierophant": "A tall piece with a triple crown stands between two rooks, one hand suggested by the carving as raised. Two pawn attendants. Crossed keys on the base. No human bodies.",
        "the-lovers": "Two pieces, one black and one white, stand apart and do not touch. A taller piece behind them spreads a carved pair of wings. Two small trees, one with a serpent, one with fruit. No human bodies.",
        "the-chariot": "A rook cut as a chariot, with a star canopy and a standing piece inside. Two knight-sphinxes, one black and one white, stand in front. A city of pieces recedes. No human bodies.",
        "strength": "A white piece rests against a lion-piece, the carved hands at its mouth. An infinity on the crown. A ring of small flowers on the base. No human bodies.",
        "the-hermit": "A lone gray pawn on a high rank, a staff, and a lantern token that lights only the next square. The rest of the board falls into dark. No human bodies.",
        "wheel-of-fortune": "A wheel inlaid in the center of the board. A sphinx piece with a sword at the top, a jackal piece climbing, a snake piece descending. Four corner pieces: angel, eagle, lion, bull. No human bodies.",
        "justice": "A white queen between two rook pillars, a sword and level scales carved on the stem. No human bodies.",
        "the-hanged-man": "A pawn is shown head-down, one foot resting on a tau-shaped piece, the other leg crossed, a halo ring. A chosen, still pause. No human bodies. No injury and no rope.",
        "death": "A black knight on a white horse-base carries a banner with one rose. A fallen king, a standing bishop, a small pawn, and a sun token between two rooks. No human bodies.",
        "temperance": "An angel-piece pours between two cup tokens. One foot on a pale water square, one on stone. A path of squares runs to a far piece topped with light. No human bodies.",
        "the-tower": "A tall rook is struck by a lightning token and loses a crown. Two pawns lie toppled in front. A red curtain behind the board. No human bodies.",
        "the-star": "A kneeling pawn by an inlaid pool, two jug tokens pouring. One large star token and seven small ones. A bird token in a small tree. No human bodies.",
        "the-moon": "A moon token between two rooks. A dog pawn and a wolf pawn flank a path of dim squares. A crayfish token in the near pool. No human bodies.",
        "the-sun": "A small pawn rides a white knight under a large sun token with straight and wavy rays. Four sunflower tokens and a wall of pawns. No human bodies.",
        "judgement": "An angel piece with a trumpet and a flag stands over open box-shaped pieces, from which pawns rise. No human bodies.",
        "the-world": "A dancer piece turns inside a wreath inlay, a rod in each hand. Four corner pieces: angel, eagle, lion, bull. No human bodies.",
    },
}

LOCK_SPECIAL = {
    "minimal-geometric": "Flat vector shapes on a strict grid. Palette limited to black, cream, and one red accent. No rendered light and no texture except a faint paper grain.",
    "glass-and-chrome": "Polished metal and smoked glass in a gallery. Soft light, mirrored floor. No costume and no facial features beyond the silhouette.",
    "gear-engine-robotics": "Gears, engines, iron, and brass only. Rivets, oil, and furnace light. No skin and no workbench.",
    "rorschach": "Strict left-right symmetry. Black ink on warm paper, blooms and spatters, almost no drawn contour. A wide empty margin.",
    "ruler-compass-pen": "Every curve is a compass arc and every edge is ruled. Center marks and construction lines stay. No wash and no color fill.",
    "suit-and-dress": "Tailored black suit, white shirt, or a satin dress only. No armor, wings, or fantasy costume on the bodies. Studio light, marble, and a gold frame.",
    "chess-pieces": "Physical chess pieces on a black-and-white marble board. Carved stone and metal, candlelight, a gold frame. No human bodies.",
}


FRAME_OPENING = {
    "art-nouveau": "Vertical 2:3 tarot card. The whiplash border is the edge of the card: cream and gold scrolls, lilies, grapevines, and pomegranates, with an arched inner opening. The ornament reaches all four edges. No black margin outside the frame. Place the numeral in a small cartouche at the top center and the English title on a cream banner at the bottom center. No extra words, no watermark, no signature.",
    "colored-pencil": "Vertical 2:3 tarot card. A double gold line with corner scrolls frames the drawing and sits on the edge of the sheet. Crescent moons and stars occupy the upper corners, and small marks sit on the side rails. The pencil work fills that frame. No black margin outside the border. Place the numeral at the top center and the English title on the bottom banner. No extra words, no watermark, no signature.",
    "cubism": "Vertical 2:3 tarot card. A thin double rule sits just inside all four edges on aged paper, and the painted planes run to that rule. No floating card and no black margin outside the rules. Place the numeral at the top center between the rules and the English title in large capitals at the bottom center. No extra words, no watermark, no signature.",
    "cyber-mysticism": "Vertical 2:3 tarot card. A thin gold geometric frame, with circles and diamonds at the corners, sits just inside all four edges. The dark scene fills that frame. No extra black band outside the gold line. Place the numeral in a small box at the top center and the English title at the bottom center. No extra words, no watermark, no signature.",
    "gear-engine-robotics": "Vertical 2:3 tarot card. A brass frame of rivets and corner bosses is the edge of the card. No black margin outside the metal. Place the numeral in a small brass plaque at the top center and the English title on a brass nameplate at the bottom center. No extra words, no watermark, no signature.",
    "glass-and-chrome": "Vertical 2:3 tarot card. A thin bright-metal frame with slightly rounded corners is the edge of the card. The gallery fills that frame. No dark margin outside the metal line. Place the numeral in a small break at the top center and the English title in a rounded plaque at the bottom center. No extra words, no watermark, no signature.",
    "neo-deco": "Vertical 2:3 tarot card. A heavy gold geometric border of stepped corners and chevrons reaches all four edges. No black margin outside the gold. Place the numeral in a circle at the top center and the English title in a black rectangle with stepped gold ends at the bottom center. No extra words, no watermark, no signature.",
    "suit-and-dress": "Vertical 2:3 tarot card. A thin gold line with corner ornaments is the edge of the card, and the photograph fills it. No black margin outside the gold line. Place the numeral in a circle at the top center and the English title in the lower gold panel. No extra words, no watermark, no signature.",
    "ancient-egypt": "Vertical 2:3 tarot card. Hieroglyph columns and a lotus border are the edge of the card and reach all four sides. A winged sun sits at the top. No black margin outside the border. Place the numeral at the top center under the winged sun and the English title on the bottom band between lotus flowers. No extra words, no watermark, no signature.",
}


def headers() -> dict[str, str]:
    text = MD.read_text()
    found = {}
    for part in re.split(r"(?m)^### ", text)[1:]:
        sid = part.split("\n", 1)[0].strip()
        body = re.search(r"```\n(.*?)```", part, re.S).group(1).strip()
        idx = body.find("\nScene for ")
        if idx < 0:
            raise SystemExit(f"no scene in {sid}")
        header = body[:idx].strip()
        header = header.replace(
            " Chains and temptation are treated as jewelry in a high-fashion campaign.",
            "",
        )
        if sid == "botanical-art":
            header = header.replace(
                "Vertical tarot card. ",
                "Vertical tarot card in the same 2:3 proportion as the reference plates, filling the picture. "
                "A thin gold hairline border sits just inside all four edges, with only a slim equal margin of cream paper, the same inset as the reference. "
                "The border, the numeral, and the title banner are fully visible and are not cut off. No wide blank bands outside the border. ",
                1,
            )
        opening = FRAME_OPENING.get(sid)
        if opening:
            old = "Vertical tarot card. Place the numeral at the top center and the English title on a banner at the bottom center. No extra words, no watermark, no signature."
            if old not in header:
                raise SystemExit(f"frame opening missing in {sid}")
            header = header.replace(old, opening, 1)
        found[sid] = header
    return found


def existing_images(folder: Path) -> set[str]:
    names = set()
    if not folder.is_dir():
        return names
    for path in folder.iterdir():
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            names.add(path.stem)
    return names


def scene_for(style: str, card_id: str, template: str, title: str) -> str:
    if style in SPECIAL:
        body = SPECIAL[style][card_id]
        return f"{body} {LOCK_SPECIAL[style]}"
    who = WHO[style]
    body = template.format(who=who)
    lock = LOCK[style].format(title=title)
    return f"{body} {lock}"


# Card back. The frame comes from the face prompt; the scene does not name a card.
BACK = {
    "editorial-luxury": "A white rose set in a round gold medallion on black silk, with a quiet repeat of small gold links. Ivory inside a thin gold frame. No model. Black, ivory, and metallic gold only.",
    "minimal-geometric": "The rose is five circles and a few arcs at the center of a strict grid. Black, cream, and one red accent. Flat shapes, a faint paper grain, and a repeating empty module.",
    "neo-deco": "A brass rose in a black-lacquer roundel. Stepped corners and chevrons repeat. One deep jewel tone sits in the center. The top circle and the bottom rectangle stay empty. Straight lines only.",
    "cyber-mysticism": "A glass rose held in thin gold rings on dark glass, with a few holographic diamonds. The top box and the bottom line stay empty. Sparse, not cluttered.",
    "brutalist-graphic": "Black, red, and cream blocks, with ink grain and misregistration. A red circle is the rose. No letters anywhere.",
    "surreal-photography": "A real white rose on dark stone, photographed, the same spray repeated in quiet impossible architecture. Gallery light. No person.",
    "glass-and-chrome": "A clear glass rose standing in a chrome ring on a mirrored floor. Smoked glass and soft light. The top break and the bottom plaque are empty metal. No figure.",
    "japanese-contemporary-poster": "A flat black ink rose, a little gold leaf, large bare cream paper, and one red disc. Not ukiyo-e. No characters.",
    "neo-symbolism": "One large white rose alone in a thin ring. Muted slate, bone, and dull gold. Worn paint and an almost empty ground.",
    "luxury-ui": "A luminous rose mark on a dark glass panel, gold hairlines, and one soft glow. No labels. An instrument, not a painting.",
    "wayang-kulit": "Punched leather, gold, crimson, and turquoise filigree forming a rose. Warm light behind the screen. Floral side panels. No puppet.",
    "greek-sculpture": "A marble roundel carved with one rose, gold leaf on the petals, photographed among columns. Chisel marks and veins stay. No statue of a body.",
    "cubism": "The rose broken into ochre, teal, brick, black, and cream planes. Canvas weave stays visible, and the paint runs to the double rule. No face.",
    "plastic-model-diorama": "The reverse of the wooden base. A white rose built from painted plastic parts and tiny gears, glue seams visible, the metal plate blank. The same desk and the same shallow focus.",
    "french-doll": "Silk, lace, and ribbon in a symmetrical pattern around a porcelain rose. Candlelight. Black, ivory, and burgundy. No doll.",
    "botanical-art": "A botanical plate of one white rose, every vein and thorn drawn in fine ink and watercolor, with small leaves repeating in the margin. Cream paper and the hairline gold border. No figure.",
    "gear-engine-robotics": "A rose assembled from gears and brass leaves, furnace light, and rivets. The top plaque and the bottom nameplate are blank metal. No skin, and no machine shaped like a person.",
    "rorschach": "One ink rose, a mirrored blot, with the same blot repeated from top to bottom. Black ink on warm paper, a wide empty margin, and hairline corner marks. Almost no contour.",
    "ruler-compass-pen": "A rose of compass arcs with the center mark left in, a ruled border, and the construction lines kept. No wash and no color fill.",
    "suit-and-dress": "A white rose photographed on marble between black suiting cloth and ivory satin. The top circle and the lower panel are empty. No person.",
    "unkei-kaikei": "A rose carved into the back of the wooden panel. Worn pigment, chisel marks, and cracks stay visible. No face and no inlaid eyes.",
    "stained-glass": "A rose window. Lead lines divide every petal. Ruby, cobalt, gold, and emerald glow because the light comes through the glass. No figure.",
    "tile-mosaic": "Small tiles and visible grout build a rose medallion. Gold, cream, black, and terracotta. Star medallions occupy the corners. No figure.",
    "chess-pieces": "The black-and-white marble board alone, a white rose inlaid at the center, a gold frame, candlelight, and a reflective floor. No pieces.",
    "art-nouveau": "One white rose under the arch. Whiplash lilies and vines stay in the border. Peacock green, cream, and gold. The cartouche and the banner are empty ornament. No figure, no stepped brass, and no sunburst.",
    "classic-tarot": "A flat repeating flower woodcut in mineral color on foxed paper, one crude white rose in a circle, and a plain black rule. No scene.",
    "ancient-egypt": "A flat pattern on aged papyrus. A white rose among lotus flowers, with a winged sun at both ends. Mineral red, turquoise, gold, and black. No profile figure and no readable signs.",
    "engraving": "A rose in a roundel, dense burin line, corner roundels, and warm laid paper. No color and no figure. The banner is empty.",
    "mezzotint": "A rose scraped out of velvety black, sepia on warm paper. The dark band is empty. No crosshatching and no figure.",
    "colored-pencil": "A white rose in visible directional strokes, red, indigo, ochre, and gold, inside the double gold frame. The corner stars repeat. No figure.",
    "watercolor": "A white rose in a thin wash, indigo, burnt sienna, and a little gold. The paper shows through, and a faint wreath repeats. No figure.",
    "sumi-e": "One ink rose with a dry-brush edge. Most of the paper is blank. Two small red seals sit opposite each other and are not characters. No calligraphy.",
}

BACK_RULE = (
    "This is the back of the card, one plate shared by the whole deck. "
    "The reference supplies the frame, the proportion, and the materials only. Replace the whole inner scene. "
    "Do not place a numeral, an English title, or any letter. "
    "No words, no watermark, no signature."
)

BACK_END = (
    "No people, no animals, no creatures, and no tarot scene. "
    "Symmetrical from left to right, and the same picture after a half turn."
)

# Second-paragraph clauses that would pull a figure or a title back in.
BACK_HEADER_FIX = {
    "editorial-luxury": ("sculptural human figure, ", ""),
    "surreal-photography": ("dreamlike human figure, ", ""),
    "glass-and-chrome": (
        "abstract human form, gallery installation aesthetic, minimal but highly symbolic. The figures are sculptures in a room, not painted people. No costume, no facial features beyond the silhouette.",
        "gallery installation of glass objects, minimal but highly symbolic. No figure.",
    ),
    "french-doll": (
        "Antique French bisque-doll photograph. Porcelain skin, glass eyes, blushed cheeks, ringlets, silk, lace, and ribbons. Candlelight. Black, ivory, and burgundy. Elegant and uncanny, with ball joints visible. No gore.",
        "Antique French doll-maker's cloth and porcelain, without a doll. Silk, lace, and ribbons. Candlelight. Black, ivory, and burgundy.",
    ),
    "suit-and-dress": (
        "Contemporary fashion photograph. The people wear a tailored black suit, a white shirt, a narrow tie, and a satin evening dress. No fantasy costume on the bodies. Studio light, marble, and a gold frame.",
        "Contemporary fashion photograph of cloth and marble only. Black suiting, ivory satin, studio light, and a gold frame. No person.",
    ),
    "greek-sculpture": (
        "Photographed classical marble sculpture in a temple interior. White stone bodies, gold leaf, dark green-black marble, Corinthian columns. Museum lighting, chisel marks, veins in the stone. A photograph of statues, not an illustration.",
        "Photographed classical marble in a temple interior. Gold leaf, dark green-black marble, Corinthian columns. Museum lighting, chisel marks, veins in the stone. A carved panel, not a statue and not an illustration.",
    ),
    "wayang-kulit": (
        "Indonesian wayang kulit shadow-puppet card. Black leather silhouettes pierced with dense gold, crimson, and turquoise filigree. Elongated arms, profile faces, white-and-red puppet masks, punched-hole patterns. Warm light behind a screen. Temple and cloud shapes in the side panels, floral puppet-theater frame.",
        "Indonesian wayang kulit leather. Black leather pierced with dense gold, crimson, and turquoise filigree. Punched-hole flowers. Warm light behind a screen. A floral frame. No puppet and no face.",
    ),
    "brutalist-graphic": (
        "Brutalist contemporary tarot poster, oversized typography, raw geometric blocks, stark contrast, rough print texture, asymmetrical composition, confrontational symbolism, experimental editorial design. Ink grain, misregistration, and cut-paper blocks.",
        "Brutalist contemporary tarot poster, raw geometric blocks, stark contrast, rough print texture, experimental editorial design. Ink grain, misregistration, and cut-paper blocks. No typography.",
    ),
    "japanese-contemporary-poster": ("subtle asymmetry, ", ""),
    "botanical-art": (
        "Flowers and fruit are drawn with the same precision as the figures.",
        "Flowers and leaves are drawn with scientific precision.",
    ),
    "neo-symbolism": (
        "Contemporary symbolic painting, monumental central figure, sparse dreamlike landscape, psychologically charged objects, muted sophisticated palette, modern figurative art, poetic and enigmatic visual narrative. Few ornaments. Each object should read as one clear symbol. Worn paint, muted slate, bone, and dull gold.",
        "Contemporary symbolic painting, one object, a sparse ground, muted sophisticated palette. Few ornaments. Worn paint, muted slate, bone, and dull gold.",
    ),
    "sumi-e": (
        "Japanese sumi ink on paper. Black and gray only, plus two small red seals. Splatter, dry brush, and a large unpainted ground. Calligraphic, not a Western wash painting.",
        "Japanese sumi ink on paper. Black and gray only, plus two small red seals. Splatter, dry brush, and a large unpainted ground. Not a Western wash painting. No calligraphy.",
    ),
}


def back_header(style: str, header: str) -> str:
    if style == "plastic-model-diorama":
        return (
            "Vertical photograph, the same proportion as the face cards. Shallow depth of field. "
            "The reverse of the wooden base sits on the modeler's desk, with a cutting mat, brushes, and paint bottles in the foreground and workshop shelves behind. "
            "Built from plastic model kits and paint, with glue seams. The metal nameplate is blank. "
            + BACK_RULE
        )
    if style == "unkei-kaikei":
        return (
            "Vertical photograph of the reverse of a temple wood panel, presented as a tarot card. "
            + BACK_RULE
            + "\n\nJapanese wood carving in the Kamakura manner. Worn mineral pigment, chisel marks, cracks, and flaked paint stay visible. Photographed as a real panel."
        )
    header = header.replace(
        "The border, the numeral, and the title banner are fully visible and are not cut off.",
        "The border is fully visible and is not cut off.",
    )
    if style == "ancient-egypt":
        header = header.replace(
            "Hieroglyph columns and a lotus border are the edge of the card and reach all four sides. A winged sun sits at the top.",
            "A lotus border is the edge of the card and reaches all four sides. A winged sun sits at both ends.",
        )
        header = header.replace(
            "Ancient Egyptian tomb painting on aged papyrus. Flat profile figures, no perspective and no modeled shading. Mineral red, turquoise, gold, and black. Hieroglyph columns, wedjat eyes, and a lotus border.",
            "Ancient Egyptian ornament on aged papyrus. No perspective and no modeled shading. Mineral red, turquoise, gold, and black. A lotus border. No readable signs.",
        )
    if style == "colored-pencil":
        header = header.replace(
            "Crescent moons and stars occupy the upper corners, and small marks sit on the side rails.",
            "Crescent moons and stars occupy every corner, and the same small marks sit on every rail.",
        )
    fix = BACK_HEADER_FIX.get(style)
    if fix:
        old, new = fix
        if old not in header:
            raise SystemExit(f"back header fix missing in {style}")
        header = header.replace(old, new, 1)
    new_header, n = re.subn(
        r"(?:Place the numeral|The numeral is carved|The numeral and the English title are printed).*?No extra words, no watermark, no signature\.",
        BACK_RULE,
        header,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit(f"numeral sentence not found in {style}")
    return new_header


def write_backs(style_headers: dict[str, str]) -> int:
    missing = [sid for sid in style_headers if sid not in BACK]
    extra = [sid for sid in BACK if sid not in style_headers]
    if missing or extra:
        raise SystemExit(f"back mismatch missing={missing} extra={extra}")
    written = 0
    for sid, header in style_headers.items():
        text = f"{back_header(sid, header)}\n\nBack: {BACK[sid]} {BACK_END}\n"
        (DESIGN / sid / "back.txt").write_text(text)
        written += 1
    return written


def main() -> None:
    style_headers = headers()
    print(f"backs {write_backs(style_headers)}")
    missing_styles = [sid for sid in list(WHO) + list(SPECIAL) if sid not in style_headers]
    extra = [sid for sid in style_headers if sid not in WHO and sid not in SPECIAL]
    if missing_styles or extra:
        raise SystemExit(f"style mismatch missing={missing_styles} extra={extra}")

    written = 0
    skipped = []
    for sid, header in style_headers.items():
        folder = DESIGN / sid
        have = existing_images(folder)
        for card_id, numeral, title, template in CARDS:
            if card_id in have or card_id == "the-devil":
                skipped.append(f"{sid}/{card_id}")
                continue
            text = f"{header}\n\nScene for {numeral}, {title}: {scene_for(sid, card_id, template, title)}\n"
            path = folder / f"{card_id}.txt"
            path.write_text(text)
            written += 1
    print(f"wrote {written}")
    print("skipped", ", ".join(skipped))


if __name__ == "__main__":
    main()
