graph [
  name "topology"
  node [
    id 0
    label "node-a"
    resource [
      cpu 30000
      memory 7992000
      storage 990000
    ]
    capacity [
      cpu 32000
      memory 8192000
      storage 1000000
    ]
    zone "default"
    zone "Zone_X"
    zone "Zone_Y"
    pdc 1
    capability [
      ssd 0
      gpu 0
    ]
    pod [
      Pod_1 [
        demand [
          cpu 1000
          memory 100000
          storage 10000
          ssd 0
          gpu 0
        ]
        prefer [
          cpu 2000
          memory 200000
          storage 10000
          ssd 1
          gpu 0
        ]
        zone "default"
        zone "Zone_X"
        collocated 1
        metadata [
          name "Pod_1"
        ]
      ]
    ]
    metadata [
      name "Node_A"
      ip "192.168.0.1"
      architecture "amd64"
      os "Linux"
    ]
  ]
  node [
    id 1
    label "node-b"
    resource [
      cpu 64000
      memory 10240000
      storage 1000000
    ]
    capacity [
      cpu 64000
      memory 10240000
      storage 1000000
    ]
    zone "default"
    zone "Zone_X"
    zone "Zone_Y"
    pdc 0
    capability [
      ssd 1
      gpu 1
    ]
    pod [
    ]
    metadata [
      name "Node_B"
      ip "192.168.0.2"
      architecture "amd64"
      os "Linux"
    ]
  ]
  edge [
    source 0
    target 1
    delay 10
    bw 100
  ]
]
