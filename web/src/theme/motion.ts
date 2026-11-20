/**
 * One orchestrated moment: on first load the two result lists settle into their order, row by row. After that,
 * motion only answers an action: switching an example re-deals the rows; a live search's hits arrive the same way.
 */
export const motion = { quick: 0.16, settle: 0.42, stagger: 0.06, ease: [0.2, 0.7, 0.2, 1] as const } as const;
