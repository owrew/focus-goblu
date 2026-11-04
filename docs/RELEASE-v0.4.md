# Focus Goblu 0.4.0

- Today puts the live chart and pet above the camera and alert detail. Live chart gaps represent unavailable tracking. The waterfall and frosted panels remain.
- Phone Check 2.0 measures six seconds per view for the screen, case and edge. It alternates full and cropped inputs, ignores duplicate detector packets and requires an explicit Apply. Diagnostic sampling pauses session accounting.
- The camera health panel shows observed resolution, face-processing rate, latency, face visibility and lighting guidance. Alert receipts store the rule, elapsed away time, trigger threshold and available detector score.
- The reaction delay is configurable from 2 to 300 seconds. The face and iris ratios are calibrated to a natural screen look. Phone context uses a broad camera-image look cone. Optional hand landmarks support a proximity estimate for handheld phones, bottles, cups, remotes and books with Balanced YOLOX. Unknown categories, exact fixation and actual phone usage remain unverified.
- Sleep the goblin uses a monotonic three-minute countdown, a potion, breathing and snore effects, then a stretch. Monitoring and analytics continue. Sound follows the app sound toggle. Fierce personalities can run and break a cartoon phone. Edge effects are click-through and can be disabled independently.
- The archive compares the most recent 7, 30 or 90 dates with the immediately preceding period. Demo sessions are excluded and the current period includes today. Reports are standalone HTML and can be printed from a browser.
- Existing settings and sessions use the same SQLite schema. Camera images stay in memory.

## Local checks

The test suite covers the five-minute threshold, object geometry, unique phone samples, explicit calibration apply, nap and wake behavior, comparison date boundaries and offline report export. In a diagnostic run on five local COCO128 images labeled with phones, center cropping raised one image's top phone-class score from 0.092 to 0.249, and one image scored zero both ways. These are candidate scores from a small offline sample and do not measure webcam accuracy.

## Acceptance on your desk

Start the camera, calibrate while looking at the screen and run Phone Check 2.0. Record the front, back and edge results at your normal desk distance. Test looking at the screen with a phone nearby, typing and reading, then sustained attention toward a visible phone in your hand. Check the receipt and reported observation rate. Lighting, webcam placement and device appearance affect detection. Earlier 720p performance observations refer to v0.3.

## Artwork

The built-in image generation tool produced two transparent four-pose sprite sheets in the app's assets folder. Qt renders the quadrants as individual poses with easing, movement and overlays.

- anime-goblin.png prompt: “Production sprite sheet, true alpha, identical original green anime goblin as reference. 2x2 grid exact quadrants with broad transparent gaps. TOP LEFT relaxed standing frontal, TOP RIGHT fists raised yelling, BOTTOM LEFT drinking from an amber potion flask held to lips, BOTTOM RIGHT curled up asleep. Same cloaked woodland character, smooth illustrated anatomy, amber eyes and tiny tusks, natural moss green shading, whole silhouettes fit each cell. Transparent pixels immediately outside every character silhouette, use a clean video-game sprite cutout with no semitransparent smoke, no gray haze, no rim glow beyond outline, no shadow, no noise, no ground or decorative marks, no text. Same art finish as transparent reference.”
- anime-motion.png prompt: “Create a transparent 2 by 2 video game sprite sheet. Match the exact anime moss-green goblin from the reference (same amber eyes, green skin, tousled dark hair, charcoal cloak, leather belt, tiny tusks), full body and centered in each equal quadrant with generous separation. Top left: waking up with both arms reaching high in a big stretch, eyes closed and yawning. Top right: dynamic running pose to the right, front knee high, cloak flaring. Bottom left: opposite running stride to the right, cloak flaring. Bottom right: cheerful inquisitive expression leaning forward and looking to its right. Clean cutout, true transparent RGBA background, no haze, no floor, no glows outside silhouette, no text. Match the shape, softly rendered anime cel shading, and scale from reference.”
