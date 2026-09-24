##Orthophoto Harmonization - Work in Progress

Next steps: 
- Harmonize skript/split functions from main script
- Implementation of new gdal application
- GPU for ovr-calculation

Pipeline

1. Define input parameters
   - input path
   - output name ⟶ KonGEO: "bundesland_tragersystem_jahr_gebiet_datentyp_auftrageber"
   - no data value ⟶ if not 0, Null or NoData
   - output projection ⟶ EPSG:25832
2. Create subfolders 
3. Build VRT from original images

   ![grafik](https://github.com/user-attachments/assets/7d7a0347-d5ae-4634-82a3-fc6aa1a9c2b5)

5. Read the metadata of the input data VRT
   - coordinate system/projection
   - number of bands
   - data type (8-bit, 16-bit...)   
6. Get the extent of the input tiles as vector data ⟶ dissolve

    ![grafik](https://github.com/user-attachments/assets/7067f93b-4f43-49fd-986d-7e4862667819)


7. If EPSG is not 25832 reprojection of the VRT and extent vector data
8. Read the metadata of the reprojected VRT
   - resolution
   - raster origin
   - raster width
   - raster hight
9. Split VRT extent into tiles
   - Tile size: 2000 x 2000 m
   - easting/northing of the lower left corner: even thousand (e.g. 614000 x 5782000)
   - write into tile extents into a list
   
   ![grafik](https://github.com/user-attachments/assets/891601c7-63c1-4bfa-ad0b-402f06dfc61f)



10. Intersect tiles with the dissolved extent of input tiles (6.) ⟶ Remove the tiles that do not intersect

     ![grafik](https://github.com/davidkunze/mosaic-creation/assets/133227408/39004eb5-c5be-4fe3-9532-9247cb943f56)  
     ![grafik](https://github.com/user-attachments/assets/efffc543-c0cf-4692-b450-2c897b2eff4c)




11. Create COG tiles
12. Metadata vector files
   - Vector files from COG tile extent without no data areas
   
     ![grafik](https://github.com/davidkunze/mosaic-creation/assets/133227408/2ecb2f60-d06b-4832-badf-f83bf910bf32)

   - dissolve of the vector files without no data areas

     ![grafik](https://github.com/davidkunze/mosaic-creation/assets/133227408/6a2f3bc7-d53e-43f9-9bef-582e5aa3e179)

   - vector files from COG tile extent including no data areas 
   
     ![grafik](https://github.com/user-attachments/assets/e5b4b5d6-6011-4ecd-b4be-129bfb41a9b2)


12. Appand metadata table (.csv) to metadata vector files

    ![grafik](https://github.com/davidkunze/mosaic-creation/assets/133227408/6c9562f6-b2bf-43e3-b193-4a62e9a9dd5c)

13. Create VRT from COG + overviews

    ![grafik](https://github.com/user-attachments/assets/7d7a0347-d5ae-4634-82a3-fc6aa1a9c2b5)
   
14. Remove temporary data

  


