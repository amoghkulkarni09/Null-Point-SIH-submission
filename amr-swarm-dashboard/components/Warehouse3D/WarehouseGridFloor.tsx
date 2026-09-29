"use client";

interface Props {
  width?: number;
  length?: number;
}

/**
 * Warehouse floor: concrete slab, painted traffic lanes, dock strip, perimeter curb.
 */
export function WarehouseGridFloor({ width = 44, length = 44 }: Props) {
  const half = width / 2;
  return (
    <group>
      {/* Concrete slab */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[width + 4, length + 4]} />
        <meshStandardMaterial color="#c5c0b5" roughness={0.98} metalness={0} />
      </mesh>

      {/* Inner floor (slightly lighter work area) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
        <planeGeometry args={[width, length]} />
        <meshStandardMaterial color="#d2cdc3" roughness={0.96} metalness={0} />
      </mesh>

      {/* Soft grid for scale */}
      <gridHelper args={[width, 44, "#b5aea2", "#c9c3b8"]} position={[0, 0.001, 0]} />

      {/* Main cross aisles — safety yellow */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]}>
        <planeGeometry args={[0.55, length - 2]} />
        <meshBasicMaterial color="#e8b923" transparent opacity={0.55} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]}>
        <planeGeometry args={[width - 2, 0.55]} />
        <meshBasicMaterial color="#e8b923" transparent opacity={0.55} />
      </mesh>

      {/* Lane edge lines */}
      {([-0.45, 0.45] as number[]).map((o) => (
        <group key={o}>
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[o, 0.016, 0]}>
            <planeGeometry args={[0.06, length - 4]} />
            <meshBasicMaterial color="#f5f0e6" transparent opacity={0.7} />
          </mesh>
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.016, o]}>
            <planeGeometry args={[width - 4, 0.06]} />
            <meshBasicMaterial color="#f5f0e6" transparent opacity={0.7} />
          </mesh>
        </group>
      ))}

      {/* Perimeter dark curb */}
      {(
        [
          [0, half + 0.4, width + 2, 0.8],
          [0, -half - 0.4, width + 2, 0.8],
          [half + 0.4, 0, 0.8, length + 2],
          [-half - 0.4, 0, 0.8, length + 2],
        ] as [number, number, number, number][]
      ).map(([x, z, w, d], i) => (
        <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[x, 0.02, z]}>
          <planeGeometry args={[w, d]} />
          <meshStandardMaterial color="#5a5550" roughness={0.9} />
        </mesh>
      ))}
    </group>
  );
}
