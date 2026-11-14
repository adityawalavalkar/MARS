const PALETTE = ['#ff7a3d', '#f3d9cc', '#c1440e', '#2fbfa5', '#e2c460', '#8c3e1e']
export const pickColor = (item, i) => item.color || PALETTE[i % PALETTE.length]
