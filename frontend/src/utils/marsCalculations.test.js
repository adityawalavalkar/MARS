import test from 'node:test'
import assert from 'node:assert/strict'
import { calculateMarsTraverse, surfaceDistanceKm } from './marsCalculations.js'

test('one degree longitude arc at Mars equator is about 59.17 km', () => {
  assert.ok(Math.abs(surfaceDistanceKm({ lat: 0, lon: 0 }, { lat: 0, lon: 1 }) - 59.17) < 0.02)
})

test('traverse calculation reports terrain, climb, sols and passability', () => {
  const result = calculateMarsTraverse({
    start: { lat: 0, lon: 0 }, end: { lat: 0, lon: 0.01 },
    profile: { distancesKm: [0, 0.5, 1], elevations: [0, 20, 40] },
  })
  assert.equal(result.ascentM, 40)
  assert.equal(result.descentM, 0)
  assert.ok(result.terrainDistanceKm > 1)
  assert.ok(result.travelSols > 0)
  assert.ok(result.averagePowerW > 0)
  assert.deepEqual(result.impassableSegments, [])
})

test('slope segments steeper than 25 degrees are flagged impassable', () => {
  const result = calculateMarsTraverse({
    start: { lat: 0, lon: 0 }, end: { lat: 0.01, lon: 0 },
    profile: { distancesKm: [0, 0.1, 0.2], elevations: [0, 100, 100] },
  })
  assert.deepEqual(result.impassableSegments, [0])
  assert.ok(result.maxSlopeDeg > 25)
})
