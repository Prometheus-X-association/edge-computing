graph [
  name "pod"
  node [
    id 0
    label "pod"
    demand [
      cpu 4
      memory 200
      storage 0
      ssd 0
      gpu 1
    ]
    prefer [
      cpu 8
      memory 1000
      storage 0
      ssd 1
      gpu 1
    ]
    zone "Zone_Y"
    collocated 0
    metadata [
      name "Pod_2"
    ]
  ]
]
