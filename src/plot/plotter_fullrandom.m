%% Plotter_Fullrandom.m
%
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%
%   [+] Fecha: 1 Mar 2025
clc
close all
clear varibles

base_path = "../results/ieee123_fullrandom/";
root_folders = dir(fullfile(base_path, "root_*"));

for i = 1:length(root_folders)
    root_path = fullfile(base_path, root_folders(i).name);
    disp("Procesando: " + root_path);
    
    close all
    plotDeltaLoads(0, root_path);
    plotRangeLoads(0, 95, root_path);
    plotTemporalBalance(0, 95, root_path);
end

% Inicializar matrices para almacenar datos de todos los roots
num_roots = length(root_folders);
num_deltas = 96; 
num_criteria = 4; 

% Matriz para almacenar los datos de todos los roots
data3d_all_roots = zeros(num_criteria, 10, num_deltas, num_roots);

for r = 1:num_roots
    root_path = fullfile(base_path, root_folders(r).name);
    
    for d = 0:num_deltas-1
        file_path = fullfile(root_path, strcat("csv/outdata_d", num2str(d), ".csv"));
        
        if exist(file_path, 'file')
            data_table = readtable(file_path, 'NumHeaderLines', 1);
            data = data_table{:,:};
            selected_criteria = [1, 3, 4, 5];
            data3d_all_roots(:, :, d+1, r) = data(selected_criteria, :);
        end
    end
end

% Calcular promedio y desviación estándar
data_avg_all = mean(data3d_all_roots, 4);
sem_all = std(data3d_all_roots, [], 4) / sqrt(num_roots);

% Generar gráficos para los datos combinados
result_path = fullfile(base_path, "global_results/");
if ~exist(result_path, 'dir')
    mkdir(result_path);
end

plotBarWithErrors(mean(data_avg_all(:, [2 4 6], :), 3), sem_all(:, [2 4 6], :), result_path, 'powerBalance_all_roots.pdf', "Balance de potencias global (Todos los Roots)", "Potencia (kW)");
plotBarWithErrors(mean(data_avg_all(:, [3 5 7], :), 3), sem_all(:, [3 5 7], :), result_path, 'powerAbsFlux_all_roots.pdf', "Flujo absoluto de potencia (Todos los Roots)", "Potencia (kW)");
plotBarWithErrors(mean(data_avg_all(:, [8 9 10], :), 3), sem_all(:, [8 9 10], :), result_path, 'timestamps_all_roots.pdf', "Tiempos de cálculo (Todos los Roots)", "Tiempo (ms)");

