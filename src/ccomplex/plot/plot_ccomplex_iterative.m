close all;
clearvars;

% Directorio de resultados (contiene subcarpetas topo_xxx/)
resultsDir = 'results_iterative';

% Lista de directorios topo_*
topoDirs = dir(fullfile(resultsDir, 'topo_*'));
numTopos = length(topoDirs);

% Prealocar
topoSizes = zeros(numTopos,1);
avgTimes  = zeros(numTopos,4); % columnas: Hops, lowLinksLoss, Power2Zero, Power2Zero+Links

% Nombre esperado de las columnas en los CSV (por si hay que comparar)
criteriaNames = {'Hops(s)', 'lowLinksLoss(s)', 'Power2Zero(s)', 'Power2Zero+Links(s)'};

for k = 1:numTopos
    fld = topoDirs(k).name;
    % extraer tamaño de la topología: topo_XXXX
    tok = regexp(fld, 'topo_(\d+)', 'tokens');
    if isempty(tok)
        warning('Nombre de carpeta no coincide con topo_NNN: %s. Se ignora.', fld);
        topoSizes(k) = NaN;
        continue;
    end
    topoSizes(k) = str2double(tok{1}{1});
    
    % listar archivos run_*.csv dentro de la carpeta de la topología
    runFiles = dir(fullfile(resultsDir, fld, 'run_*.csv'));
    if isempty(runFiles)
        warning('No se han encontrado run_*.csv en %s. Se pone NaN.', fullfile(resultsDir,fld));
        avgTimes(k,:) = NaN;
        continue;
    end
    
    % matriz temporal para las medias por run (cada fila = un run, 4 columnas = criterios)
    runMeans = nan(length(runFiles), 4);
    
    for r = 1:length(runFiles)
        csvPath = fullfile(resultsDir, fld, runFiles(r).name);
        try
            T = readtable(csvPath);
        catch ME
            warning('Error leyendo %s : %s', csvPath, ME.message);
            continue;
        end
        
        % Comprobar que haya al menos 5 columnas (Delta + 4 criterios)
        if width(T) < 5
            warning('Fichero %s no tiene el formato esperado (menos de 5 columnas).', csvPath);
            continue;
        end
        
        % Tomamos las columnas 2:end como tiempos (ignoramos la columna 'Delta')
        data = T{:, 2:min(5,width(T))}; % protege si hay columnas extra
        % Si hay más de 4 columnas de tiempos, recortamos a 4 (esperado)
        if size(data,2) > 4
            data = data(:,1:4);
        elseif size(data,2) < 4
            % intentar mapear por nombres si el orden es distinto
            % en ese caso intentamos buscar por nombre de columna
            cols = zeros(1,4);
            for c = 1:4
                idx = find(strcmp(T.Properties.VariableNames, criteriaNames{c}),1);
                if ~isempty(idx)
                    cols(c) = idx;
                else
                    cols(c) = NaN;
                end
            end
            if all(~isnan(cols))
                data = T{:, cols};
            else
                warning('No se han encontrado las 4 columnas de criterios en %s. Se ignora este run.', csvPath);
                continue;
            end
        end
        
        % media sobre las deltas (filas)
        runMeans(r, :) = mean(data, 1, 'omitnan');
    end
    
    % media entre runs (media de las medias de cada run) -> doble promedio
    % descartamos filas NaN (runs fallidos)
    valid = ~any(isnan(runMeans),2);
    if any(valid)
        avgTimes(k, :) = mean(runMeans(valid, :), 1, 'omitnan');
    else
        avgTimes(k, :) = NaN;
        warning('Todos los runs para %s fallaron o estaban mal formateados.', fld);
    end
end

% Eliminar entradas sin tamaño válido o sin datos
validTopos = ~isnan(topoSizes) & ~all(isnan(avgTimes),2);
topoSizes = topoSizes(validTopos);
avgTimes  = avgTimes(validTopos, :);

% Ordenar por tamaño
[topoSizes, ord] = sort(topoSizes);
avgTimes = avgTimes(ord, :);

% Ploteo
figure('Units','normalized','Position',[0.05 0.1 0.9 0.5]);
hold on;
markers = {'o-','s-','d-','^-'};
for c = 1:4
    plot(topoSizes, avgTimes(:,c), markers{c}, 'LineWidth',1.6, 'MarkerSize',6);
end
xlabel('Graph size (nodes)', 'FontSize', 14);
ylabel('Tiempo medio de ejecución [s]', 'FontSize', 14);
title('Complejidad computacional del proceso iterativo', 'FontSize', 16);
legend(criteriaNames, 'Location','northwest','FontSize',12);
grid on;
set(gca, 'YScale', 'log');
ax = gca;
ax.XAxis.FontSize = 12;
ax.YAxis.FontSize = 12;
xlim([min(topoSizes) max(topoSizes)]);
hold off;

% Exportar la figura a PDF vectorial
outputFile = fullfile(resultsDir, 'iterative_complexity_double_average.pdf');
exportgraphics(gcf, outputFile, 'ContentType','vector');
fprintf('Figura exportada a %s\n', outputFile);
